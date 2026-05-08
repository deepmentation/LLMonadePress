from __future__ import annotations

import json
from dataclasses import dataclass

import litellm


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


@dataclass
class LLMClient:
    default_model: str = "anthropic/claude-haiku-4-5"

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]
        usage = response.usage or {}

        return LLMResponse(
            content=choice.message.content or "",
            model=model,
            tokens_in=getattr(usage, "prompt_tokens", 0),
            tokens_out=getattr(usage, "completion_tokens", 0),
            cost_usd=litellm.completion_cost(response) or 0.0,
        )

    async def complete_json(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> tuple[dict | list, LLMResponse]:
        response = await self.complete(
            prompt=prompt,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = (response.content or "").strip()
        if not content:
            raise RuntimeError(
                f"LLM ({response.model}) returned empty content. "
                "Common cause: missing or invalid API key for that provider. "
                "Set the right *_API_KEY in .env, or switch ranker_model / "
                "writer_model in config.toml to a provider you have a key for "
                "(e.g. ollama/qwen3:14b for fully local, or "
                "openrouter/anthropic/claude-sonnet-4 if you only have an "
                "OpenRouter key)."
            )
        # Local models often wrap JSON in prose or ```json fences. Try to find
        # the JSON object inside the response before failing.
        try:
            return json.loads(content), response
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(content[start : end + 1]), response
                except json.JSONDecodeError:
                    pass
            raise RuntimeError(
                f"LLM ({response.model}) did not return valid JSON. "
                f"First 200 chars: {content[:200]!r}. "
                "If this is a local model, try a more capable one "
                "(qwen3:14b or larger) or set a stricter system prompt."
            ) from None


async def get_embeddings(texts: list[str], model: str = "openai/text-embedding-3-small") -> list[list[float]]:
    response = await litellm.aembedding(model=model, input=texts)
    return [item["embedding"] for item in response.data]
