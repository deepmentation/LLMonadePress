from __future__ import annotations

from lemonade.llm.client import LLMClient, LLMResponse
from lemonade.llm.prompts.rank import build_rank_prompt, build_rank_system
from lemonade.pipeline.cluster import Cluster


async def rank_clusters(
    clusters: list[Cluster],
    max_stories: int,
    client: LLMClient,
    model: str | None = None,
    language: str = "en",
) -> tuple[list[dict], LLMResponse]:
    cluster_dicts = [
        {
            "id": c.id,
            "title": c.title,
            "text": c.text,
            "source_type": c.source_type,
            # Breadth signal — how many distinct sources cover this story.
            "source_count": len(c.sources) or len(c.item_ids) or 1,
            "source_types": sorted({s.get("type", c.source_type) for s in c.sources}),
        }
        for c in clusters
    ]
    prompt = build_rank_prompt(cluster_dicts, max_stories, language=language)
    result, response = await client.complete_json(
        prompt=prompt,
        model=model,
        system=build_rank_system(language),
    )
    # Accept either {"ranked": [...]} or a bare list of ranked entries —
    # different providers and prompt-following levels produce both shapes.
    if isinstance(result, list):
        items = result
    elif isinstance(result, dict):
        items = result.get("ranked") or result.get("clusters") or []
    else:
        items = []
    ranked = list(items)[:max_stories]
    return ranked, response
