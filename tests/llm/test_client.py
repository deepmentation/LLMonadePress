import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from lemonade.llm.client import LLMClient, LLMResponse

@pytest.mark.asyncio
async def test_complete_returns_response():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello"))]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    with patch("lemonade.llm.client.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        with patch("lemonade.llm.client.litellm.completion_cost", return_value=0.001):
            client = LLMClient()
            result = await client.complete("test prompt")
            assert result.content == "Hello"
            assert result.tokens_in == 10

@pytest.mark.asyncio
async def test_complete_json_parses():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"key": "value"}'))]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    with patch("lemonade.llm.client.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        with patch("lemonade.llm.client.litellm.completion_cost", return_value=0.0):
            client = LLMClient()
            data, resp = await client.complete_json("test")
            assert data == {"key": "value"}
