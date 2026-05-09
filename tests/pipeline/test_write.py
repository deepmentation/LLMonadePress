import pytest
from unittest.mock import AsyncMock, patch
from lemonade.pipeline.write import write_story, WrittenStory
from lemonade.pipeline.cluster import Cluster
from lemonade.llm.client import LLMClient, LLMResponse

@pytest.mark.asyncio
async def test_write_story():
    cluster = Cluster(id="c1", title="Test", text="Some text", urls=["https://example.com"])
    mock_result = {
        "headline": "Test Headline",
        "deck": "A short deck.",
        "body": "Body text here.",
        "category": "Tech",
        "sources": [{"title": "Example", "url": "https://example.com", "domain": "example.com"}],
    }
    client = LLMClient()
    with patch.object(client, "complete_json", new_callable=AsyncMock, return_value=(mock_result, LLMResponse(content="", model="test"))):
        story, resp = await write_story(cluster, client)
        assert story.headline == "Test Headline"
        assert story.cluster_id == "c1"


@pytest.mark.asyncio
async def test_write_story_uses_authoritative_sources_when_present():
    """If the cluster carries enriched sources from the DB, those win
    over whatever the LLM hallucinated."""
    cluster = Cluster(
        id="c1", title="Test", text="x",
        urls=["https://heise.de/a"],
        sources=[{
            "item_id": "i1", "title": "Real", "url": "https://heise.de/a",
            "domain": "heise.de", "type": "rss", "published_at": "2026-05-09T10:00:00+00:00",
            "channel_name": "heise online",
        }],
    )
    mock_result = {
        "headline": "h", "deck": "d", "body": "b", "category": "c",
        "sources": [{"title": "Made up", "url": "https://other.com", "domain": "other.com"}],
    }
    client = LLMClient()
    with patch.object(client, "complete_json", new_callable=AsyncMock,
                      return_value=(mock_result, LLMResponse(content="", model="t"))):
        story, _ = await write_story(cluster, client)
    assert story.sources == cluster.sources
    assert story.sources[0]["channel_name"] == "heise online"


@pytest.mark.asyncio
async def test_write_story_falls_back_to_llm_sources_when_no_metadata():
    cluster = Cluster(id="c1", title="t", text="x", urls=["https://example.com"], sources=[])
    mock_result = {
        "headline": "h", "deck": "d", "body": "b", "category": "c",
        "sources": [{"title": "X", "url": "https://example.com", "domain": "example.com"}],
    }
    client = LLMClient()
    with patch.object(client, "complete_json", new_callable=AsyncMock,
                      return_value=(mock_result, LLMResponse(content="", model="t"))):
        story, _ = await write_story(cluster, client)
    assert story.sources[0]["domain"] == "example.com"
