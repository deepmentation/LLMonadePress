import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from lemonade.adapters.rss import RSSAdapter

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Test Article</title>
      <link>https://example.com/article</link>
      <guid>article-1</guid>
      <pubDate>Thu, 08 May 2026 10:00:00 GMT</pubDate>
      <description>This is the article summary text for testing.</description>
    </item>
    <item>
      <title>Old Article</title>
      <link>https://example.com/old</link>
      <guid>article-old</guid>
      <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
      <description>Old content.</description>
    </item>
  </channel>
</rss>"""

@pytest.fixture
def adapter():
    return RSSAdapter()

@pytest.fixture
def parsed_feed():
    import feedparser
    return feedparser.parse(SAMPLE_RSS)

@pytest.mark.asyncio
async def test_fetch_parses_items(adapter, parsed_feed):
    with patch("lemonade.adapters.rss.feedparser.parse", return_value=parsed_feed):
        items = await adapter.fetch("https://example.com/feed.xml", {}, datetime(2024, 6, 1, tzinfo=timezone.utc))
        assert len(items) == 1
        assert items[0].title == "Test Article"
        assert items[0].external_id == "article-1"

@pytest.mark.asyncio
async def test_fetch_filters_old_items(adapter, parsed_feed):
    with patch("lemonade.adapters.rss.feedparser.parse", return_value=parsed_feed):
        items = await adapter.fetch("https://example.com/feed.xml", {}, datetime(2026, 5, 9, tzinfo=timezone.utc))
        assert len(items) == 0

@pytest.mark.asyncio
async def test_fetch_extracts_text(adapter, parsed_feed):
    with patch("lemonade.adapters.rss.feedparser.parse", return_value=parsed_feed):
        items = await adapter.fetch("https://example.com/feed.xml", {}, datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert "article summary text" in items[0].raw_text
