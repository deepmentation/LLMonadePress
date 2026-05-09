import pytest
from unittest.mock import AsyncMock, patch
from llmonadepress.pipeline.write import write_story, WrittenStory
from llmonadepress.pipeline.cluster import Cluster
from llmonadepress.llm.client import LLMClient, LLMResponse

_VALID_RESULT = {
    "headline": "A Reasonable Headline Here",
    "deck": "A short deck describing the article.",
    "body": "Body text here. " * 20,  # well over the 80-char minimum
    "category": "Tech",
    "sources": [{"title": "Example", "url": "https://example.com", "domain": "example.com"}],
}


@pytest.mark.asyncio
async def test_write_story():
    cluster = Cluster(id="c1", title="Test", text="Some text", urls=["https://example.com"])
    client = LLMClient()
    with patch.object(client, "complete_json", new_callable=AsyncMock,
                      return_value=(_VALID_RESULT, LLMResponse(content="", model="test"))):
        story, _resp = await write_story(cluster, client)
        assert story.headline == "A Reasonable Headline Here"
        assert story.cluster_id == "c1"


@pytest.mark.asyncio
async def test_write_story_retries_on_short_body():
    """First attempt returns garbage, second returns a valid story.
    write_story should retry with an explanatory hint and ship the good one."""
    cluster = Cluster(id="c1", title="t", text="x", urls=["u"])
    bad = {"headline": "Hi", "deck": "d", "body": "short", "category": "c"}

    call_count = {"n": 0}

    async def mock_complete(prompt, **_):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return bad, LLMResponse(content="", model="t")
        # On retry the prompt should mention what was wrong
        assert "RETRY" in prompt
        return _VALID_RESULT, LLMResponse(content="", model="t")

    client = LLMClient()
    with patch.object(client, "complete_json", side_effect=mock_complete):
        story, _ = await write_story(cluster, client)
    assert call_count["n"] == 2
    assert story.headline == "A Reasonable Headline Here"


@pytest.mark.asyncio
async def test_write_story_gives_up_after_max_attempts():
    """If every attempt fails validation, return the last (incomplete) story
    so the caller can drop it explicitly."""
    cluster = Cluster(id="c1", title="t", text="x", urls=["u"])
    bad = {"headline": "", "deck": "", "body": "", "category": "c"}
    client = LLMClient()
    with patch.object(client, "complete_json", new_callable=AsyncMock,
                      return_value=(bad, LLMResponse(content="", model="t"))) as mock_call:
        story, _ = await write_story(cluster, client)
    assert mock_call.call_count == 3  # _MAX_ATTEMPTS
    assert story.headline == ""


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
