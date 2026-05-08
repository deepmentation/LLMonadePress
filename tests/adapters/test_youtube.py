import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from lemonade.adapters.youtube import YouTubeAdapter

SAMPLE_YT_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <entry>
    <yt:videoId>dQw4w9WgXcQ</yt:videoId>
    <title>Test Video</title>
    <author><name>Test Channel</name></author>
    <published>2026-05-08T10:00:00+00:00</published>
    <link rel="alternate" href="https://www.youtube.com/watch?v=dQw4w9WgXcQ"/>
  </entry>
</feed>"""

@pytest.fixture
def adapter():
    return YouTubeAdapter()

@pytest.fixture
def parsed_feed():
    import feedparser
    return feedparser.parse(SAMPLE_YT_FEED)

@pytest.mark.asyncio
async def test_fetch_with_transcript(adapter, parsed_feed):
    with patch("lemonade.adapters.youtube.feedparser.parse", return_value=parsed_feed):
        with patch.object(adapter, "_get_transcript", return_value={"text": "Hello world", "source": "native_en"}):
            items = await adapter.fetch("UC123", {}, datetime(2024, 1, 1, tzinfo=timezone.utc))
            assert len(items) == 1
            assert items[0].external_id == "dQw4w9WgXcQ"
            assert items[0].raw_text == "Hello world"

@pytest.mark.asyncio
async def test_fetch_skips_without_transcript(adapter, parsed_feed):
    with patch("lemonade.adapters.youtube.feedparser.parse", return_value=parsed_feed):
        with patch.object(adapter, "_get_transcript", return_value=None):
            items = await adapter.fetch("UC123", {}, datetime(2024, 1, 1, tzinfo=timezone.utc))
            assert len(items) == 0
