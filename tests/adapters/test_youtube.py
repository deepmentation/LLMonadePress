from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lemonade.adapters.youtube import YouTubeAdapter


SINCE = datetime(2024, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def adapter():
    return YouTubeAdapter()


def _videos(*tuples):
    """Helper: build the dicts our discovery layer hands to fetch()."""
    return [
        {"id": vid, "title": title, "duration_s": dur, "uploader": "TestChannel"}
        for vid, title, dur in tuples
    ]


@pytest.mark.asyncio
async def test_fetch_uses_discovery_and_transcript(adapter):
    videos = _videos(("vid1", "Test Video", 600))
    with patch.object(adapter, "_list_recent_videos", AsyncMock(return_value=videos)), \
         patch.object(adapter, "_get_transcript",
                      AsyncMock(return_value={"text": "Hello world", "source": "native_en"})):
        items = await adapter.fetch("UC123", {}, SINCE)

    assert len(items) == 1
    assert items[0].external_id == "vid1"
    assert items[0].raw_text == "Hello world"
    assert items[0].metadata["source_type"] == "youtube"
    assert items[0].metadata["transcript_source"] == "native_en"
    assert items[0].metadata["duration_s"] == 600


@pytest.mark.asyncio
async def test_fetch_skips_videos_without_transcript(adapter):
    videos = _videos(("vid1", "x", 600))
    with patch.object(adapter, "_list_recent_videos", AsyncMock(return_value=videos)), \
         patch.object(adapter, "_get_transcript", AsyncMock(return_value=None)):
        items = await adapter.fetch("UC123", {}, SINCE)
    assert items == []


@pytest.mark.asyncio
async def test_fetch_filters_shorts_by_min_duration(adapter):
    videos = _videos(
        ("short", "Short", 30),
        ("long", "Long form", 600),
    )
    with patch.object(adapter, "_list_recent_videos", AsyncMock(return_value=videos)), \
         patch.object(adapter, "_get_transcript",
                      AsyncMock(return_value={"text": "ok", "source": "native_en"})):
        items = await adapter.fetch("UC123", {"min_duration_s": 180}, SINCE)
    assert [it.external_id for it in items] == ["long"]


@pytest.mark.asyncio
async def test_fetch_passes_handle_to_discovery(adapter):
    with patch.object(adapter, "_list_recent_videos",
                      AsyncMock(return_value=[])) as mock_disc:
        await adapter.fetch("@somehandle", {}, SINCE)
    mock_disc.assert_awaited_once_with("https://www.youtube.com/@somehandle/videos")


@pytest.mark.asyncio
async def test_fetch_passes_channel_id_to_discovery(adapter):
    cid = "UC123456789012345678901a"  # 24 chars starting with UC
    with patch.object(adapter, "_list_recent_videos",
                      AsyncMock(return_value=[])) as mock_disc:
        await adapter.fetch(cid, {"channel_id": cid}, SINCE)
    mock_disc.assert_awaited_once_with(f"https://www.youtube.com/channel/{cid}/videos")


@pytest.mark.asyncio
async def test_list_recent_videos_uses_yt_dlp_flat_in_playlist():
    adapter = YouTubeAdapter()
    fake_info = {
        "channel": "ColeMedin",
        "entries": [
            {"_type": "url", "id": "abc", "title": "first", "duration": 100.0},
            {"_type": "url", "id": "def", "title": "second", "duration": None},
        ],
    }
    fake_ydl = MagicMock()
    fake_ydl.__enter__ = MagicMock(return_value=fake_ydl)
    fake_ydl.__exit__ = MagicMock(return_value=False)
    fake_ydl.extract_info = MagicMock(return_value=fake_info)
    fake_module = MagicMock(YoutubeDL=MagicMock(return_value=fake_ydl))
    with patch.dict("sys.modules", {"yt_dlp": fake_module}):
        result = await adapter._list_recent_videos("https://example.com")

    assert result == [
        {"id": "abc", "title": "first", "duration_s": 100, "uploader": "ColeMedin"},
        {"id": "def", "title": "second", "duration_s": None, "uploader": "ColeMedin"},
    ]
    # Confirm we asked for the cheap flat mode.
    opts_passed = fake_module.YoutubeDL.call_args[0][0]
    assert opts_passed["extract_flat"] == "in_playlist"
    assert opts_passed["playlistend"] == YouTubeAdapter.DISCOVERY_LIMIT


@pytest.mark.asyncio
async def test_resolve_handle_uses_yt_dlp():
    adapter = YouTubeAdapter()
    fake_info = {"channel_id": "UCabcdef0123456789012345"}
    fake_ydl = MagicMock()
    fake_ydl.__enter__ = MagicMock(return_value=fake_ydl)
    fake_ydl.__exit__ = MagicMock(return_value=False)
    fake_ydl.extract_info = MagicMock(return_value=fake_info)
    fake_module = MagicMock(YoutubeDL=MagicMock(return_value=fake_ydl))
    with patch.dict("sys.modules", {"yt_dlp": fake_module}):
        result = await adapter._resolve_handle("@example")
    assert result == "UCabcdef0123456789012345"
