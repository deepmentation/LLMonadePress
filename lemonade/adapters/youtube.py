from __future__ import annotations

import re
from datetime import datetime, UTC

import feedparser

from lemonade.adapters.base import FetchedItem, SourceAdapter


class YouTubeAdapter(SourceAdapter):
    CHANNEL_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    async def fetch(self, identifier: str, config: dict, since: datetime) -> list[FetchedItem]:
        channel_id = config.get("channel_id") or identifier
        if channel_id.startswith("@"):
            channel_id = await self._resolve_handle(channel_id)

        feed_url = self.CHANNEL_FEED.format(channel_id=channel_id)
        feed = feedparser.parse(feed_url)

        items = []
        for entry in feed.entries:
            video_id = getattr(entry, "yt_videoid", None) or self._extract_video_id(entry)
            if not video_id:
                continue

            published = self._parse_date(entry)
            if published and published < since:
                continue

            transcript = await self._get_transcript(video_id, config)
            if transcript is None:
                continue

            items.append(FetchedItem(
                external_id=video_id,
                url=f"https://youtube.com/watch?v={video_id}",
                title=entry.get("title"),
                author=entry.get("author"),
                published_at=published,
                raw_text=transcript["text"],
                metadata={
                    "source_type": "youtube",
                    "transcript_source": transcript["source"],
                },
            ))
        return items

    def _extract_video_id(self, entry) -> str | None:
        link = entry.get("link", "")
        match = re.search(r"v=([a-zA-Z0-9_-]{11})", link)
        return match.group(1) if match else None

    def _parse_date(self, entry) -> datetime | None:
        for field in ("published", "updated"):
            val = entry.get(field)
            if val:
                try:
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(val).astimezone(UTC)
                except Exception:
                    try:
                        return datetime.fromisoformat(val.replace("Z", "+00:00"))
                    except Exception:
                        pass
        return None

    async def _get_transcript(self, video_id: str, config: dict) -> dict | None:
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

        # Tier 3: Whisper (deferred — return None for now if no captions)
        return None

    async def _resolve_handle(self, handle: str) -> str:
        """Resolve a @handle to a channel ID. Stub — returns handle as-is for now."""
        return handle
