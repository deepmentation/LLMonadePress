from __future__ import annotations

RANK_SYSTEM = """Du bist ein Nachrichtenredakteur. Bewerte Story-Cluster nach Relevanz, Neuheit und Tiefe."""

def build_rank_prompt(clusters: list[dict], max_stories: int) -> str:
    cluster_text = ""
    for i, c in enumerate(clusters):
        cluster_text += f"\n### Cluster {i+1} (ID: {c['id']})\n"
        cluster_text += f"Titel: {c['title']}\n"
        cluster_text += f"Quelle: {c.get('source_type', 'unknown')}\n"
        cluster_text += f"Text (gekürzt): {c['text'][:500]}\n"

    return f"""Du bekommst {len(clusters)} Story-Cluster. Bewerte jedes nach:
- relevance (0–10): Wichtigkeit unabhängig vom User
- novelty (0–10): wie neu ist die Information
- depth (0–10): substantieller Beitrag vs. Boulevard

Wähle die Top-{max_stories} aus.

Antwort als JSON: {{"ranked": [{{"cluster_id": "...", "relevance": N, "novelty": N, "depth": N, "score": N, "reason": "..."}}]}}

{cluster_text}"""
