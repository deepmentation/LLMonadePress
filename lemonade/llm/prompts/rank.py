from __future__ import annotations

from lemonade.llm.prompts.i18n import get_prompts


def build_rank_system(language: str) -> str:
    return get_prompts(language).rank_system


def build_rank_prompt(clusters: list[dict], max_stories: int, language: str) -> str:
    p = get_prompts(language)

    cluster_text = ""
    for i, c in enumerate(clusters, start=1):
        cluster_text += "\n" + p.rank_cluster_header.format(n=i, id=c["id"]) + "\n"
        cluster_text += f"{p.rank_label_title}: {c['title']}\n"
        cluster_text += f"{p.rank_label_source}: {c.get('source_type', 'unknown')}\n"
        cluster_text += f"{p.rank_label_text}: {c['text'][:500]}\n"

    return (
        p.rank_intro.format(n=len(clusters))
        + "\n"
        + f"- {p.rank_criteria_relevance}\n"
        + f"- {p.rank_criteria_novelty}\n"
        + f"- {p.rank_criteria_depth}\n\n"
        + p.rank_select.format(max_stories=max_stories)
        + "\n\n"
        + p.rank_response_hint
        + "\n"
        + cluster_text
    )
