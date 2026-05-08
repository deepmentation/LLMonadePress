# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.4] — 2026-05-08

### Fixed
- `lemonade init` no longer fails with `type "vector" does not exist`. The
  bootstrap now runs `CREATE EXTENSION IF NOT EXISTS vector` before
  `Base.metadata.create_all`, so a fresh Postgres database can be initialised
  in one command. The Alembic migration already did this for managed schema
  changes; the gap was in the convenience bootstrap path.
- `docker-compose.yml` now overrides `DATABASE_URL` to point at the `db`
  service hostname for the app container. The default value in `.env` keeps
  pointing at `localhost` so non-Docker development setups still work.

### Docs
- README quickstart split into separate code blocks. zsh's
  `interactive_comments` is off by default — trailing `# comment` text in
  pasted multi-line snippets becomes positional arguments and produces
  confusing errors. Each step is now its own block with prose between them.

## [0.1.3] — 2026-05-08

### Fixed
- App container no longer crash-loops when `config.toml` is missing.
  Lemonade is a batch job, not a daemon — `docker compose up` now starts
  only the database, and pipeline runs are invoked explicitly via
  `docker compose run --rm app …`.
- `load_config()` raises a helpful `IsADirectoryError` when Docker's bind
  mount has auto-created `config.toml` as an empty directory (the previous
  failure mode), and `FileNotFoundError` with a clear next step when the
  file is simply missing.

### Changed
- The `app` service in `docker-compose.yml` now uses the `manual` Compose
  profile so it is excluded from `docker compose up` by default.
- Dockerfile `CMD` defaults to `--help` (was `run`) — running with no
  arguments now prints usage instead of attempting a pipeline run.
- README quickstart updated to reflect the new flow and warns about the
  bind-mount-auto-creates-empty-directory pitfall.

## [0.1.2] — 2026-05-08

### Fixed
- Docker build now succeeds. The previous Dockerfile copied only
  `pyproject.toml` before `pip install .`, leaving hatchling without sources to
  build a wheel from. Sources, profiles, templates, and Alembic migrations are
  now copied before install, and `[tool.hatch.build.targets.wheel].packages`
  declares the package explicitly.
- `device_profiles/` and `templates/` are now bundled into the wheel under
  `lemonade/_bundled/` via `force-include`, so installed installations find
  them without depending on the repo layout.
- New `lemonade/_paths.py` resolves data directories with a clean precedence:
  `LEMONADE_PROFILES_DIR` / `LEMONADE_TEMPLATES_DIR` env override → bundled
  copy → repo-root copy. Editable installs and pip installs both work.

### Added
- `.dockerignore` to keep `.venv/`, caches, and tests out of the build context
  (build context dropped from ~580 MB to a few MB).

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

[Unreleased]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lemonade-newspaper/lemonade/releases/tag/v0.1.0
