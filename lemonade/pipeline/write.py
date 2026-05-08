from __future__ import annotations

from dataclasses import dataclass

from lemonade.llm.client import LLMClient, LLMResponse
from lemonade.llm.prompts.write import WRITE_SYSTEM, build_write_prompt
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
    language: str = "de",
) -> tuple[WrittenStory, LLMResponse]:
    prompt = build_write_prompt(
        {"title": cluster.title, "text": cluster.text, "urls": cluster.urls},
        language=language,
    )
    result, response = await client.complete_json(
        prompt=prompt,
        model=model,
        system=WRITE_SYSTEM,
    )
    story = WrittenStory(
        headline=result.get("headline", ""),
        deck=result.get("deck", ""),
        body=result.get("body", ""),
        category=result.get("category", ""),
        sources=result.get("sources", []),
        pull_quote=result.get("pull_quote"),
        cluster_id=cluster.id,
    )
    return story, response


async def write_edition(
    clusters: list[Cluster],
    ranked: list[dict],
    client: LLMClient,
    model: str | None = None,
    language: str = "de",
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
