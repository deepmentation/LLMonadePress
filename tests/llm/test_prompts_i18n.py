import pytest

from llmonadepress.llm.prompts.i18n import (
    DEFAULT_LANGUAGE,
    PROMPTS,
    SUPPORTED_LANGUAGES,
    get_prompts,
)
from llmonadepress.llm.prompts.rank import build_rank_prompt, build_rank_system
from llmonadepress.llm.prompts.write import build_write_prompt, build_write_system


def test_supported_languages_include_en_de_fr():
    assert "en" in SUPPORTED_LANGUAGES
    assert "de" in SUPPORTED_LANGUAGES
    assert "fr" in SUPPORTED_LANGUAGES


def test_all_packs_define_all_fields():
    en_fields = set(PROMPTS["en"].__dataclass_fields__)
    for lang in SUPPORTED_LANGUAGES:
        assert set(PROMPTS[lang].__dataclass_fields__) == en_fields
        for field_name in en_fields:
            value = getattr(PROMPTS[lang], field_name)
            assert isinstance(value, str) and value, f"{lang}.{field_name} is empty"


def test_get_prompts_falls_back_to_default():
    assert get_prompts("zz") is PROMPTS[DEFAULT_LANGUAGE]


def test_get_prompts_is_case_insensitive():
    assert get_prompts("DE") is PROMPTS["de"]


@pytest.mark.parametrize("lang", ["en", "de", "fr"])
def test_build_rank_prompt_contains_clusters_and_criteria(lang):
    clusters = [
        {"id": "c1", "title": "Headline A", "text": "Body A", "source_type": "rss"},
        {"id": "c2", "title": "Headline B", "text": "Body B", "source_type": "youtube"},
    ]
    prompt = build_rank_prompt(clusters, max_stories=1, language=lang)
    assert "Headline A" in prompt
    assert "c1" in prompt
    assert "relevance" in prompt
    assert "novelty" in prompt
    assert "depth" in prompt


@pytest.mark.parametrize("lang", ["en", "de", "fr"])
def test_build_write_prompt_contains_source_and_rules(lang):
    cluster = {
        "title": "Some Title",
        "text": "Source body text.",
        "urls": ["https://example.com/a", "https://example.com/b"],
    }
    prompt = build_write_prompt(cluster, language=lang)
    assert "Some Title" in prompt
    assert "https://example.com/a" in prompt
    assert "headline" in prompt
    assert "80" in prompt and "150" in prompt


@pytest.mark.parametrize("lang", ["en", "de", "fr"])
def test_system_prompts_per_language(lang):
    assert build_rank_system(lang) == PROMPTS[lang].rank_system
    assert build_write_system(lang) == PROMPTS[lang].write_system


def test_rank_prompt_de_uses_german_labels():
    prompt = build_rank_prompt(
        [{"id": "c1", "title": "T", "text": "x", "source_type": "rss"}],
        max_stories=1,
        language="de",
    )
    assert "Titel:" in prompt
    assert "Quelle:" in prompt


def test_rank_prompt_fr_uses_french_labels():
    prompt = build_rank_prompt(
        [{"id": "c1", "title": "T", "text": "x", "source_type": "rss"}],
        max_stories=1,
        language="fr",
    )
    assert "Titre" in prompt
    assert "Source" in prompt


def test_config_rejects_unsupported_language():
    from pydantic import ValidationError

    from llmonadepress.config import UserConfig

    with pytest.raises(ValidationError):
        UserConfig(language="zz")


def test_config_normalises_language_case():
    from llmonadepress.config import UserConfig

    assert UserConfig(language="DE").language == "de"


def test_pyproject_declares_supported_languages():
    """The [tool.llmonadepress] section in pyproject.toml is the declarative source of
    truth for supported languages — keep it in sync with the i18n registry."""
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    declared = data["tool"]["llmonadepress"]["supported_languages"]
    assert set(declared) == set(SUPPORTED_LANGUAGES)
    assert data["tool"]["llmonadepress"]["default_language"] == DEFAULT_LANGUAGE
