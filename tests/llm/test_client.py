import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from llmonadepress.llm.client import LLMClient, LLMResponse

@pytest.mark.asyncio
async def test_complete_returns_response():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello"))]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    with patch("llmonadepress.llm.client.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        with patch("llmonadepress.llm.client.litellm.completion_cost", return_value=0.001):
            client = LLMClient()
            result = await client.complete("test prompt")
            assert result.content == "Hello"
            assert result.tokens_in == 10

@pytest.mark.asyncio
async def test_complete_json_parses():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"key": "value"}'))]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    with patch("llmonadepress.llm.client.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        with patch("llmonadepress.llm.client.litellm.completion_cost", return_value=0.0):
            client = LLMClient()
            data, resp = await client.complete_json("test")
            assert data == {"key": "value"}


def test_extract_json_prefers_dict_over_inner_array():
    """Regression: a fenced article with a sources array used to be matched
    as an array (because the outer dict failed to parse for some reason),
    then unwrapped to the first source object, silently producing empty
    stories."""
    from llmonadepress.llm.client import _extract_json

    # Closing fence missing (truncated by max_tokens) — direct parse and
    # the strict fence regex both fail. Used to fall through to [...] span,
    # which matched the inner sources array.
    content = (
        '```json\n'
        '{\n'
        '  "headline": "Test Headline",\n'
        '  "body": "Body text with an "unescaped quote that breaks JSON",\n'
        '  "sources": [\n'
        '    {"title": "S1", "url": "https://a", "domain": "a"},\n'
        '    {"title": "S2", "url": "https://b", "domain": "b"}\n'
        '  ]'
    )
    result = _extract_json(content)
    # With json-repair installed we should get the dict back; without it
    # at least we should NOT silently get a source dict masquerading as
    # the article.
    if isinstance(result, dict):
        assert "headline" in result or "body" in result, (
            f"Got a source dict instead of an article: {list(result.keys())}"
        )
    else:
        # If parsing failed entirely, we want None (caller raises clear error)
        assert result is None or isinstance(result, list)


def test_extract_json_strips_leading_fence_only():
    """Sonnet sometimes opens a fence and never closes it — handle that."""
    from llmonadepress.llm.client import _extract_json

    content = '```json\n{"headline": "Hi", "body": "body"}'
    result = _extract_json(content)
    assert isinstance(result, dict)
    assert result["headline"] == "Hi"


def test_extract_json_handles_clean_fenced_dict():
    from llmonadepress.llm.client import _extract_json

    content = '```json\n{"headline": "Hi", "body": "b"}\n```'
    result = _extract_json(content)
    assert result == {"headline": "Hi", "body": "b"}


def test_extract_json_repairs_unescaped_quote_in_body():
    """Regression for a real Sonnet failure mode: the body contains an
    unescaped ASCII ``"`` (mis-typed smart quote) so strict JSON parse
    fails on the outer object. Without json-repair the extractor falls
    back to the inner ``sources: [...]`` array, and write_story ships an
    empty story. With json-repair we recover the article."""
    from llmonadepress.llm.client import _extract_json

    content = (
        '```json\n'
        '{\n'
        '  "headline": "Mit parallelen KI-Agenten zehnmal schneller",\n'
        '  "deck": "test",\n'
        '  "body": "Inspiriert vom Managementbuch „10x Is Easier Than 2x"'
        ' argumentiert der Entwickler.",\n'
        '  "category": "Technologie",\n'
        '  "sources": [{"title": "X", "url": "u", "domain": "d"}],\n'
        '  "pull_quote": "x"\n'
        '}\n'
        '```'
    )
    result = _extract_json(content)
    assert isinstance(result, dict), f"expected dict, got {type(result).__name__}"
    assert "headline" in result, f"missing headline; keys: {list(result.keys())}"
    assert "body" in result
    assert result["headline"].startswith("Mit parallelen")
