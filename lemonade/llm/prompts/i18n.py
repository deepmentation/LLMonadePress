"""Multi-language prompt templates for ranking and writing.

Each supported language provides the same set of prompt building blocks.
Adding a new language: add an entry to ``PROMPTS`` and update
``SUPPORTED_LANGUAGES`` in this module.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptPack:
    rank_system: str
    rank_intro: str
    rank_criteria_relevance: str
    rank_criteria_novelty: str
    rank_criteria_depth: str
    rank_select: str
    rank_response_hint: str
    rank_cluster_header: str
    rank_label_title: str
    rank_label_source: str
    rank_label_text: str

    write_system: str
    write_intro: str
    write_label_title: str
    write_label_text: str
    write_label_urls: str
    write_response_hint: str
    write_rules_header: str
    write_rule_headline: str
    write_rule_deck: str
    write_rule_body: str
    write_rule_pull_quote: str
    write_rule_sources: str
    write_rule_language: str


PROMPTS: dict[str, PromptPack] = {
    "en": PromptPack(
        rank_system=(
            "You are a senior news editor. Evaluate story clusters by relevance, "
            "novelty, and depth. Be precise and consistent."
        ),
        rank_intro="You will receive {n} story clusters. Rate each one on:",
        rank_criteria_relevance="relevance (0–10): general importance, independent of any reader",
        rank_criteria_novelty="novelty (0–10): how new the information is",
        rank_criteria_depth="depth (0–10): substantive contribution vs. tabloid noise",
        rank_select="Select the top {max_stories}.",
        rank_response_hint=(
            'Respond as JSON: {{"ranked": [{{"cluster_id": "...", "relevance": N, '
            '"novelty": N, "depth": N, "score": N, "reason": "..."}}]}}'
        ),
        rank_cluster_header="### Cluster {n} (ID: {id})",
        rank_label_title="Title",
        rank_label_source="Source",
        rank_label_text="Text (truncated)",
        write_system=(
            "You are an experienced newspaper editor. Write concise, informative articles "
            "in clear, journalistic English."
        ),
        write_intro="Write a newspaper article based on the following sources.",
        write_label_title="Title",
        write_label_text="Text",
        write_label_urls="URLs",
        write_response_hint=(
            "Respond as JSON with fields: headline, deck, body, category, sources "
            '(list of {{title, url, domain}}), pull_quote.'
        ),
        write_rules_header="Rules:",
        write_rule_headline="headline: at most 8 words",
        write_rule_deck="deck: exactly 1 sentence",
        write_rule_body="body: 80–150 words, NOT more",
        write_rule_pull_quote="pull_quote: optional, max 15 words",
        write_rule_sources="sources: every source you used, with its domain",
        write_rule_language="Write everything in English.",
    ),
    "de": PromptPack(
        rank_system=(
            "Du bist erfahrener Nachrichtenredakteur. Bewerte Story-Cluster nach Relevanz, "
            "Neuheit und Tiefe. Sei präzise und konsistent."
        ),
        rank_intro="Du bekommst {n} Story-Cluster. Bewerte jedes nach:",
        rank_criteria_relevance="relevance (0–10): generelle Wichtigkeit, unabhängig vom Leser",
        rank_criteria_novelty="novelty (0–10): wie neu die Information ist",
        rank_criteria_depth="depth (0–10): substantieller Beitrag vs. Boulevard",
        rank_select="Wähle die Top-{max_stories} aus.",
        rank_response_hint=(
            'Antwort als JSON: {{"ranked": [{{"cluster_id": "...", "relevance": N, '
            '"novelty": N, "depth": N, "score": N, "reason": "..."}}]}}'
        ),
        rank_cluster_header="### Cluster {n} (ID: {id})",
        rank_label_title="Titel",
        rank_label_source="Quelle",
        rank_label_text="Text (gekürzt)",
        write_system=(
            "Du bist erfahrener Zeitungsredakteur. Schreibe prägnante, informative Artikel "
            "in klarem, journalistischem Deutsch."
        ),
        write_intro="Schreibe einen Zeitungsartikel basierend auf folgenden Quellen.",
        write_label_title="Titel",
        write_label_text="Text",
        write_label_urls="URLs",
        write_response_hint=(
            "Antwort als JSON mit Feldern: headline, deck, body, category, sources "
            "(Liste aus {{title, url, domain}}), pull_quote."
        ),
        write_rules_header="Regeln:",
        write_rule_headline="headline: maximal 8 Wörter",
        write_rule_deck="deck: genau 1 Satz",
        write_rule_body="body: 80–150 Wörter, NICHT mehr",
        write_rule_pull_quote="pull_quote: optional, max 15 Wörter",
        write_rule_sources="sources: alle verwendeten Quellen mit Domain",
        write_rule_language="Schreibe alles auf Deutsch.",
    ),
    "fr": PromptPack(
        rank_system=(
            "Vous êtes un rédacteur en chef expérimenté. Évaluez les groupes d'articles "
            "selon la pertinence, la nouveauté et la profondeur. Soyez précis et cohérent."
        ),
        rank_intro="Vous recevez {n} groupes d'articles. Évaluez chacun selon :",
        rank_criteria_relevance="relevance (0–10) : importance générale, indépendamment du lecteur",
        rank_criteria_novelty="novelty (0–10) : nouveauté de l'information",
        rank_criteria_depth="depth (0–10) : contribution substantielle vs. presse à sensation",
        rank_select="Sélectionnez les {max_stories} meilleurs.",
        rank_response_hint=(
            'Répondez en JSON : {{"ranked": [{{"cluster_id": "...", "relevance": N, '
            '"novelty": N, "depth": N, "score": N, "reason": "..."}}]}}'
        ),
        rank_cluster_header="### Groupe {n} (ID : {id})",
        rank_label_title="Titre",
        rank_label_source="Source",
        rank_label_text="Texte (tronqué)",
        write_system=(
            "Vous êtes un rédacteur de presse expérimenté. Rédigez des articles concis "
            "et informatifs dans un français journalistique clair."
        ),
        write_intro="Rédigez un article de presse basé sur les sources suivantes.",
        write_label_title="Titre",
        write_label_text="Texte",
        write_label_urls="URLs",
        write_response_hint=(
            "Répondez en JSON avec les champs : headline, deck, body, category, sources "
            "(liste de {{title, url, domain}}), pull_quote."
        ),
        write_rules_header="Règles :",
        write_rule_headline="headline : 8 mots maximum",
        write_rule_deck="deck : exactement 1 phrase",
        write_rule_body="body : 80–150 mots, PAS plus",
        write_rule_pull_quote="pull_quote : optionnel, 15 mots maximum",
        write_rule_sources="sources : toutes les sources utilisées, avec leur domaine",
        write_rule_language="Rédigez tout en français.",
    ),
}

SUPPORTED_LANGUAGES: tuple[str, ...] = tuple(PROMPTS.keys())
DEFAULT_LANGUAGE = "en"


def get_prompts(language: str) -> PromptPack:
    """Return the prompt pack for ``language``. Falls back to the default."""
    return PROMPTS.get(language.lower(), PROMPTS[DEFAULT_LANGUAGE])
