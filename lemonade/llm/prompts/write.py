from __future__ import annotations

WRITE_SYSTEM = """Du bist ein erfahrener Zeitungsredakteur. Schreibe prägnante, informative Artikel."""

def build_write_prompt(cluster: dict, language: str = "de") -> str:
    return f"""Schreibe einen Zeitungsartikel basierend auf folgenden Quellen.

Sprache: {language}

Quellen:
Titel: {cluster['title']}
Text: {cluster['text'][:2000]}
URLs: {', '.join(cluster.get('urls', []))}

Antwort als JSON:
{{
  "headline": "...",
  "deck": "...",
  "body": "...",
  "category": "...",
  "sources": [{{"title": "...", "url": "...", "domain": "..."}}],
  "pull_quote": "..."
}}

Regeln:
- headline: maximal 8 Wörter
- deck: genau 1 Satz
- body: 80–150 Wörter, NICHT mehr
- pull_quote: optional, max 15 Wörter
- sources: alle verwendeten Quellen mit Domain"""
