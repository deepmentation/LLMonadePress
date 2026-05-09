from __future__ import annotations

import logging
from dataclasses import dataclass

from llmonadepress.llm.client import LLMClient, LLMResponse
from llmonadepress.llm.prompts.write import build_write_prompt, build_write_system
from llmonadepress.pipeline.cluster import Cluster

logger = logging.getLogger(__name__)

# A story is "valid enough to ship" when both headline and body have
# meaningful content. LLMs occasionally return one-word headlines or
# empty bodies even with structured-output mode; retrying with a stricter
# prompt almost always fixes it. Three attempts is more than enough.
_MIN_HEADLINE_CHARS = 8
_MIN_BODY_CHARS = 80
_MAX_ATTEMPTS = 3


def _validation_problems(result: dict) -> list[str]:
    """Return a list of human-readable issues with the story dict; empty if OK."""
    problems: list[str] = []
    headline = (result.get("headline") or "").strip()
    body = (result.get("body") or "").strip()
    if len(headline) < _MIN_HEADLINE_CHARS:
        problems.append(f"headline too short ({len(headline)} chars)")
    if len(body) < _MIN_BODY_CHARS:
        problems.append(f"body too short ({len(body)} chars)")
    return problems


@dataclass
class WrittenStory:
    headline: str
    deck: str
    body: str
    category: str
    sources: list[dict]
    pull_quote: str | None = None
    cluster_id: str = ""


async def write_story(
    cluster: Cluster,
    client: LLMClient,
    model: str | None = None,
    language: str = "en",
) -> tuple[WrittenStory, LLMResponse]:
    base_prompt = build_write_prompt(
        {"title": cluster.title, "text": cluster.text, "urls": cluster.urls},
        language=language,
    )

    result: dict = {}
    response: LLMResponse | None = None
    last_problems: list[str] = []

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if last_problems:
            prompt = (
                base_prompt
                + "\n\n--- RETRY ---\nYour previous attempt was rejected: "
                + "; ".join(last_problems)
                + ". Produce a complete article this time — every required field "
                "filled with meaningful content."
            )
        result, response = await client.complete_json(
            prompt=prompt,
            model=model,
            system=build_write_system(language),
        )
        # Some models (esp. Sonnet via OpenRouter) wrap a single object in a
        # one-element list. Unwrap defensively before accessing fields.
        if isinstance(result, list):
            result = result[0] if result else {}
        if not isinstance(result, dict):
            result = {}

        last_problems = _validation_problems(result)
        if not last_problems:
            break
        logger.warning(
            "write_story attempt %d/%d for cluster %s failed validation: %s",
            attempt, _MAX_ATTEMPTS, cluster.id, ", ".join(last_problems),
        )

    if last_problems:
        logger.error(
            "write_story exhausted %d attempts for cluster %s; "
            "shipping partial story anyway. Final problems: %s",
            _MAX_ATTEMPTS, cluster.id, ", ".join(last_problems),
        )
    # Sources come from the cluster authoritatively (real DB rows) rather
    # than from whatever the LLM chose to fabricate. Falls back to the LLM
    # output only if the cluster has no enriched metadata yet.
    sources = cluster.sources or result.get("sources", [])
    story = WrittenStory(
        headline=result.get("headline", ""),
        deck=result.get("deck", ""),
        body=result.get("body", ""),
        category=result.get("category", ""),
        sources=sources,
        pull_quote=result.get("pull_quote"),
        cluster_id=cluster.id,
    )
    return story, response


async def write_edition(
    clusters: list[Cluster],
    ranked: list[dict],
    client: LLMClient,
    model: str | None = None,
    language: str = "en",
) -> tuple[list[WrittenStory], list[LLMResponse]]:
    cluster_map = {c.id: c for c in clusters}
    stories = []
    responses = []
    for entry in ranked:
        cluster = cluster_map.get(entry["cluster_id"])
        if not cluster:
            continue
        story, resp = await write_story(cluster, client, model, language)
        if resp is not None:
            responses.append(resp)
        # Drop stories that still have no headline or body after retries —
        # better to ship fewer good articles than a section with empty cards.
        if not story.headline.strip() or not story.body.strip():
            logger.warning(
                "Dropping empty story for cluster %s after retries", cluster.id
            )
            continue
        stories.append(story)
    return stories, responses
