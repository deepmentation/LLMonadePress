from __future__ import annotations

import json
import re
from dataclasses import dataclass

import litellm


_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.+?)\n```", re.DOTALL)
_FENCE_OPEN_RE = re.compile(r"^\s*```(?:json)?\s*\n", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\n```\s*$")


def _strip_fence(content: str) -> str:
    """Strip leading/trailing markdown code fences, even if asymmetric.

    Sonnet sometimes emits ``` ```json\\n{...}\\n``` ``` cleanly; sometimes
    only the opening fence; sometimes the closing fence is missing because
    the response was truncated. Be lenient on both sides.
    """
    s = _FENCE_OPEN_RE.sub("", content)
    s = _FENCE_CLOSE_RE.sub("", s)
    return s.strip()


def _try_repair(s: str) -> dict | list | None:
    """Run ``json-repair`` on the string and return the parsed result.

    json-repair handles the LLM-typical breakage modes that strict
    ``json.loads`` chokes on: unescaped quotes inside strings (Sonnet
    occasionally emits an ASCII ``"`` instead of the smart-quote ``"`` it
    seems to be aiming for), trailing commas, unterminated values caused
    by truncation, and similar.

    Returns the parsed value (dict or list) on success, ``None`` if the
    library isn't installed or repair gives nothing useful.
    """
    try:
        from json_repair import repair_json
    except ImportError:
        return None
    try:
        repaired = repair_json(s)
    except Exception:
        return None
    if not repaired or repaired in ("{}", "[]", "null"):
        return None
    try:
        return json.loads(repaired) if isinstance(repaired, str) else repaired
    except json.JSONDecodeError:
        return None


def _extract_json(content: str) -> dict | list | None:
    """Best-effort JSON extraction from LLM output.

    Strategy:
      1. Build candidate strings (raw, fence-stripped, fence-extracted,
         {…} span, […] span).
      2. Strict-parse each candidate.
      3. If any **dict** parsed, return it (most callers want a top-level
         object — preferring a dict over a list prevents an inner
         ``"sources": [...]`` array from masquerading as the article).
      4. Otherwise try ``json-repair`` on the dict-shaped candidates;
         json-repair handles unescaped quotes / truncation / trailing
         commas that strict ``json.loads`` rejects.
      5. As a last resort, return whatever parsed (likely a list).
    """
    candidates: list[str] = []
    candidates.append(content)
    candidates.append(_strip_fence(content))

    fence = _FENCE_RE.search(content)
    if fence:
        candidates.append(fence.group(1))

    for opener, closer in (("{", "}"), ("[", "]")):
        start = content.find(opener)
        end = content.rfind(closer)
        if start != -1 and end > start:
            candidates.append(content[start : end + 1])

    parsed: list[dict | list] = []
    for cand in candidates:
        try:
            parsed.append(json.loads(cand))
        except json.JSONDecodeError:
            continue

    for p in parsed:
        if isinstance(p, dict) and p:
            return p

    # No usable dict from strict parsing. Many real LLM responses look
    # like a dict but have one mis-emitted character (commonly an
    # unescaped ASCII quote inside a string body). Try to repair the
    # candidates that *look* like a dict (start with ``{``).
    for cand in candidates:
        stripped = cand.strip()
        if not stripped.startswith("{"):
            continue
        repaired = _try_repair(stripped)
        if isinstance(repaired, dict) and repaired:
            return repaired

    if parsed:
        return parsed[0]
    return None


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

        # Ollama defaults to a 2048-token context and a 128-token output —
        # both far too small for our long cluster prompts. Bump them so
        # local models behave like cloud APIs by default.
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            kwargs["num_ctx"] = 16384
            kwargs["num_predict"] = max_tokens

        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]
        usage = response.usage or {}

        # LiteLLM's pricing database lags behind new model releases; fall
        # back to 0.0 instead of letting an unknown-model lookup crash a
        # successful completion.
        try:
            cost = litellm.completion_cost(response) or 0.0
        except Exception:
            cost = 0.0

        return LLMResponse(
            content=choice.message.content or "",
            model=model,
            tokens_in=getattr(usage, "prompt_tokens", 0),
            tokens_out=getattr(usage, "completion_tokens", 0),
            cost_usd=cost,
        )

    async def complete_json(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
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
                "writer_model in config.toml to a provider you have a key for."
            )
        parsed = _extract_json(content)
        if parsed is None:
            head = content[:300]
            tail = content[-300:] if len(content) > 600 else ""
            raise RuntimeError(
                f"LLM ({response.model}) did not return valid JSON.\n"
                f"--- response head ---\n{head!r}\n"
                + (f"--- response tail ---\n{tail!r}\n" if tail else "")
                + "If the response looks truncated, raise max_tokens. "
                "If a local model, try qwen3:14b or larger and ensure "
                "ollama num_ctx is high enough for the prompt."
            )
        return parsed, response


async def get_embeddings(texts: list[str], model: str = "openai/text-embedding-3-small") -> list[list[float]]:
    response = await litellm.aembedding(model=model, input=texts)
    return [item["embedding"] for item in response.data]
