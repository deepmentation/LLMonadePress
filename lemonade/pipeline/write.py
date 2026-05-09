from __future__ import annotations

from dataclasses import dataclass

from lemonade.llm.client import LLMClient, LLMResponse
from lemonade.llm.prompts.write import build_write_prompt, build_write_system
from lemonade.pipeline.cluster import Cluster


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
    prompt = build_write_prompt(
        {"title": cluster.title, "text": cluster.text, "urls": cluster.urls},
        language=language,
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
        stories.append(story)
        responses.append(resp)
    return stories, responses
