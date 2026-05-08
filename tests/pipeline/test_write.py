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
