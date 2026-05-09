from __future__ import annotations

from llmonadepress.llm.prompts.i18n import get_prompts


def build_write_system(language: str) -> str:
    return get_prompts(language).write_system


def build_write_prompt(cluster: dict, language: str) -> str:
    p = get_prompts(language)
    urls = ", ".join(cluster.get("urls", []))

    return (
        p.write_intro
        + "\n\n"
        + f"{p.write_label_title}: {cluster['title']}\n"
        + f"{p.write_label_text}: {cluster['text'][:2000]}\n"
        + f"{p.write_label_urls}: {urls}\n\n"
        + p.write_response_hint
        + "\n\n"
        + p.write_rules_header
        + "\n"
        + f"- {p.write_rule_headline}\n"
        + f"- {p.write_rule_deck}\n"
        + f"- {p.write_rule_body}\n"
        + f"- {p.write_rule_pull_quote}\n"
        + f"- {p.write_rule_sources}\n"
        + f"- {p.write_rule_language}"
    )
