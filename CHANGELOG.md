# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] — 2026-05-08

### Added
- Multi-language prompt support with translation packs for English, German,
  and French (`lemonade/llm/prompts/i18n.py`).
- `[tool.lemonade]` section in `pyproject.toml` declaring supported output
  languages and the default language as the project-level source of truth.
- Pydantic validator on `[user] language` rejects unsupported codes and
  normalises case.
- Ranking pipeline now receives the configured language and renders both the
  system prompt and the user prompt in the chosen language.

### Changed
- Default output language is now `"en"`. Set `[user] language = "de"` (or
  `"fr"`) in `config.toml` to keep the previous behaviour.
- `build_rank_prompt` and `build_write_prompt` are language-aware end to end
  (labels, criteria, rules, and an explicit "write everything in this
  language" instruction).

### Fixed
- Dockerfile now installs Typst from the official GitHub release instead of a
  broken third-party install URL; multi-arch (amd64/arm64).
- Removed unused imports and modernised `datetime.UTC` usage across the codebase.

## [0.1.0] — 2026-05-08

Initial MVP release. Generates personalized PDF newspapers from RSS and YouTube
sources, optimized for E-Ink tablets.

### Added
- Project foundation: `pyproject.toml`, Dockerfile, Docker Compose setup
- Documentation: README, CLAUDE.md, AI-CODING-GUIDE.md, KONZEPT.md, MIT License
- GitHub issue and PR templates
- Configuration layer: TOML loader with Pydantic v2 models, ENV-based secrets
- Database layer: SQLAlchemy 2.0 async models (sources, items, editions,
  edition_items, deliveries) with pgvector embeddings
- Alembic migrations (initial schema)
- Source adapters:
  - RSS adapter via feedparser + trafilatura fulltext fallback
  - YouTube adapter with 3-tier transcript fallback
    (native captions → auto-generated → Whisper stub)
- LLM layer:
  - LiteLLM client wrapper with JSON mode and cost tracking
  - Provider-neutral support: Anthropic, OpenAI, Ollama, Groq, OpenRouter, ...
  - German-language prompts for ranking and article writing
- Curation pipeline:
  - Embedding-based clustering with cosine similarity (threshold 0.85)
  - LLM ranking by relevance / novelty / depth
  - LLM article writing with structured JSON output
- Rendering:
  - 6 device profiles (reMarkable Paper Pro Move, Paper Pro 11.8", reMarkable 2,
    Kindle Paperwhite, iPad mini, generic A5)
  - Typst templates (newspaper, cover, story, colophon)
  - Typst subprocess runner
- Delivery channels: filesystem, email (aiosmtplib), reMarkable (rmapi)
- CLI commands: `run`, `preview`, `init`, `sources list`, `devices list`,
  `email-test`
- Full pipeline orchestration (ingest → cluster → rank → write → render → deliver)
- 44 passing unit tests

[Unreleased]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lemonade-newspaper/lemonade/releases/tag/v0.1.0
