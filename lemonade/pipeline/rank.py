from __future__ import annotations

from lemonade.llm.client import LLMClient, LLMResponse
from lemonade.llm.prompts.rank import RANK_SYSTEM, build_rank_prompt
from lemonade.pipeline.cluster import Cluster


async def rank_clusters(
    clusters: list[Cluster],
    max_stories: int,
    client: LLMClient,
    model: str | None = None,
) -> tuple[list[dict], LLMResponse]:
    cluster_dicts = [
        {"id": c.id, "title": c.title, "text": c.text, "source_type": c.source_type}
        for c in clusters
    ]
    prompt = build_rank_prompt(cluster_dicts, max_stories)
    result, response = await client.complete_json(
        prompt=prompt,
        model=model,
        system=RANK_SYSTEM,
    )
    ranked = result.get("ranked", [])[:max_stories]
    return ranked, response
