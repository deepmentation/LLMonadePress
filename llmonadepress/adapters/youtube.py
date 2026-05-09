from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from llmonadepress.adapters.base import FetchedItem, SourceAdapter

logger = logging.getLogger(__name__)


class YouTubeAdapter(SourceAdapter):
    """Fetches recent videos from a YouTube channel and transcribes them.

    Discovery uses yt-dlp instead of YouTube's channel RSS endpoint
    (``feeds/videos.xml``) — that endpoint frequently 404/500s from data-
    center IPs (Docker, VPSes), while yt-dlp ships with the bypass logic
    for handle pages and channel /videos tabs.

    Transcript pipeline (3 tiers):
      1. Native captions via youtube-transcript-api
      2. Auto-generated captions via youtube-transcript-api
      3. ASR (configured via ``[asr]`` in config.toml, "off" by default)
    """

    # Newest N videos per channel per run. We rely on yt-dlp's natural
    # newest-first ordering plus DB-side dedup on (source_id, external_id)
    # instead of a timestamp filter — extract_flat (the fast path) does not
    # return upload timestamps, and the full path costs seconds per video.
    DISCOVERY_LIMIT = 10

    def __init__(self, asr_config=None):
        self.asr_config = asr_config

    async def fetch(
        self, identifier: str, config: dict, since: datetime  # noqa: ARG002 — see DISCOVERY_LIMIT note
    ) -> list[FetchedItem]:
        channel_url = self._channel_url(config.get("channel_id") or identifier)
        videos = await self._list_recent_videos(channel_url)

        min_duration = int(config.get("min_duration_s") or 0)

        items: list[FetchedItem] = []
        for video in videos:
            video_id = video.get("id")
            if not video_id:
                continue

            duration = video.get("duration_s")
            if min_duration and duration is not None and duration < min_duration:
                logger.debug("Skipping %s: duration %ds < %ds", video_id, duration, min_duration)
                continue

            transcript = await self._get_transcript(video_id)
            if transcript is None:
                continue

            items.append(FetchedItem(
                external_id=video_id,
                url=f"https://youtube.com/watch?v={video_id}",
                title=video.get("title"),
                author=video.get("uploader"),
                published_at=None,  # flat-mode discovery has no timestamps
                raw_text=transcript["text"],
                metadata={
                    "source_type": "youtube",
                    "transcript_source": transcript["source"],
                    **({"duration_s": duration} if duration is not None else {}),
                },
            ))
        return items

    @staticmethod
    def _channel_url(identifier: str) -> str:
        if identifier.startswith("@"):
            return f"https://www.youtube.com/{identifier}/videos"
        if identifier.startswith("UC") and len(identifier) == 24:
            return f"https://www.youtube.com/channel/{identifier}/videos"
        # Last-ditch: hand whatever we got to yt-dlp and hope it figures it out.
        return f"https://www.youtube.com/{identifier}"

    async def _list_recent_videos(self, channel_url: str) -> list[dict]:
        """Use yt-dlp to list recent videos. Returns dicts with id, title,
        duration_s, uploader."""
        loop = asyncio.get_event_loop()

        def _extract() -> list[dict]:
            import yt_dlp
            opts = {
                "quiet": True,
                "no_warnings": True,
                # "in_playlist" exposes id/title/duration/url for each entry
                # without resolving each video individually (that would take
                # seconds per video).
                "extract_flat": "in_playlist",
                "skip_download": True,
                "playlistend": self.DISCOVERY_LIMIT,
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(channel_url, download=False)
            except Exception:
                logger.exception("yt-dlp discovery failed for %s", channel_url)
                return []

            entries = info.get("entries") or []
            uploader = info.get("channel") or info.get("uploader")
            results: list[dict] = []
            for e in entries:
                if not e or e.get("_type") not in (None, "url", "video"):
                    continue
                results.append({
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "duration_s": int(e["duration"]) if e.get("duration") else None,
                    "uploader": uploader,
                })
            return results

        return await loop.run_in_executor(None, _extract)

    async def _get_transcript(self, video_id: str) -> dict | None:
        # Tier 1: Native captions
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            ytt = YouTubeTranscriptApi()
            t = ytt.fetch(video_id, languages=["de", "en"])
            text = " ".join(seg.text for seg in t.snippets)
            return {"text": text, "source": f"native_{t.language}"}
        except Exception:
            pass

        # Tier 2: Auto-generated captions
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            ytt = YouTubeTranscriptApi()
            t = ytt.fetch(video_id)
            text = " ".join(seg.text for seg in t.snippets)
            return {"text": text, "source": f"auto_{t.language}"}
        except Exception:
            pass

        # Tier 3: ASR (only if explicitly enabled)
        if self.asr_config and self.asr_config.backend != "off":
            try:
                return await self._asr_transcribe(video_id)
            except Exception:
                logger.exception("ASR transcription failed for %s", video_id)

        return None

    async def _resolve_handle(self, handle: str) -> str | None:
        """Resolve a @handle to a channel ID via yt-dlp's metadata extractor.

        Scraping the HTML page directly often hits YouTube's consent/anti-bot
        wall (the page contains zero ``UC…`` IDs). yt-dlp ships with the
        machinery to bypass that, so reuse it here even though we only want
        a single ID.
        """
        loop = asyncio.get_event_loop()

        def _extract() -> str | None:
            import yt_dlp
            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": 1,  # we don't need the videos, just the channel info
            }
            url = f"https://www.youtube.com/{handle}"
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception:
                logger.exception("yt-dlp failed to resolve handle %s", handle)
                return None
            for key in ("channel_id", "uploader_id", "id"):
                val = info.get(key)
                if val and isinstance(val, str) and val.startswith("UC") and len(val) == 24:
                    return val
            return None

        return await loop.run_in_executor(None, _extract)

    async def _asr_transcribe(self, video_id: str) -> dict | None:
        """Download the audio and transcribe via the configured ASR backend."""
        with tempfile.TemporaryDirectory(prefix="lemonade-yt-") as tmp:
            audio_path = await self._download_audio(video_id, Path(tmp))
            if audio_path is None:
                return None

            backend = self.asr_config.backend
            if backend == "litellm":
                text = await self._transcribe_litellm(audio_path)
                source = f"asr_litellm_{self.asr_config.model.split('/')[-1]}"
            elif backend == "faster-whisper":
                text = await self._transcribe_faster_whisper(audio_path)
                source = f"asr_faster-whisper_{self.asr_config.model_size}"
            else:
                return None

            if not text:
                return None
            return {"text": text, "source": source}

    # Whisper providers (OpenAI, OpenRouter, Groq) cap upload at 25 MB.
    # We compress to mono opus 24 kbps after download, which keeps a
    # 60-minute talk under ~11 MB without hurting speech ASR quality.
    AUDIO_BITRATE = "24k"
    AUDIO_CHANNELS = "1"

    async def _download_audio(self, video_id: str, dest_dir: Path) -> Path | None:
        """yt-dlp the audio-only stream then compress with ffmpeg.

        Returns the compressed file path (.opus). Falls back to the raw
        download if ffmpeg fails — the caller can then decide whether the
        size is acceptable.
        """
        url = f"https://youtube.com/watch?v={video_id}"
        loop = asyncio.get_event_loop()

        def _download() -> Path | None:
            import yt_dlp
            opts = {
                "format": "bestaudio/best",
                "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "m4a")
            path = dest_dir / f"{video_id}.{ext}"
            return path if path.exists() else None

        raw_path = await loop.run_in_executor(None, _download)
        if raw_path is None:
            return None

        compressed = dest_dir / f"{video_id}.opus"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(raw_path),
            "-ac", self.AUDIO_CHANNELS,
            "-b:a", self.AUDIO_BITRATE,
            "-c:a", "libopus",
            "-vn",  # drop any video stream just in case
            str(compressed),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0 or not compressed.exists():
            logger.warning(
                "ffmpeg compression failed for %s (rc=%s): %s — using raw download",
                video_id, proc.returncode, stderr.decode()[:200],
            )
            return raw_path
        # Drop the raw file to keep the temp dir small.
        try:
            raw_path.unlink()
        except OSError:
            pass
        return compressed

    async def _transcribe_litellm(self, audio_path: Path) -> str | None:
        """Send the audio file to a transcription endpoint.

        OpenRouter exposes whisper at /audio/transcriptions but with a
        custom base64-in-JSON body (not the OpenAI-compatible multipart
        form), so LiteLLM cannot route it. We detect the openrouter/
        prefix and call the REST endpoint directly. All other providers
        (Groq, OpenAI, …) go through LiteLLM normally.
        """
        model = self.asr_config.model
        if model.startswith("openrouter/"):
            return await self._transcribe_openrouter(audio_path, model.removeprefix("openrouter/"))

        import litellm
        with audio_path.open("rb") as f:
            response = await litellm.atranscription(model=model, file=f)
        text = getattr(response, "text", None)
        if text is None and isinstance(response, dict):
            text = response.get("text")
        return text

    async def _transcribe_openrouter(self, audio_path: Path, model: str) -> str | None:
        """Direct REST call against OpenRouter's transcription endpoint.

        Body shape per https://openrouter.ai/openai/whisper-large-v3-turbo/api:
            {"model": "openai/...", "input_audio": {"data": <base64>, "format": "<ext>"}}
        """
        import base64
        import os

        import httpx

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY env var is not set; cannot reach OpenRouter."
            )

        audio_bytes = audio_path.read_bytes()
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        # Strip leading dot from suffix; OpenRouter wants e.g. "m4a", "wav", "mp3"
        fmt = audio_path.suffix.lstrip(".").lower() or "m4a"

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-OpenRouter-Title": "LLMonadePress",
                },
                json={
                    "model": model,
                    "input_audio": {"data": b64, "format": fmt},
                },
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter transcription failed ({response.status_code}): "
                f"{response.text[:300]}"
            )
        result = response.json()
        return result.get("text")

    async def _transcribe_faster_whisper(self, audio_path: Path) -> str | None:
        """Local transcription via faster-whisper."""
        loop = asyncio.get_event_loop()

        def _run() -> str:
            from faster_whisper import WhisperModel
            model = WhisperModel(self.asr_config.model_size, device="cpu", compute_type="int8")
            lang = None if self.asr_config.language == "auto" else self.asr_config.language
            segments, _info = model.transcribe(str(audio_path), language=lang)
            return " ".join(seg.text for seg in segments).strip()

        return await loop.run_in_executor(None, _run)
