# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] — 2026-05-09

### Fixed
- **OpenRouter Whisper transcription works.** LiteLLM cannot route
  OpenRouter's `/audio/transcriptions` endpoint because OpenRouter
  expects a base64-in-JSON body (`input_audio: {data, format}`) instead
  of OpenAI-compatible multipart form-data. Added a direct REST path
  for `model = "openrouter/..."` that posts the correct body shape.
  Verified end-to-end on a real YouTube video.
- `config.example.toml` documents the OpenRouter caveat and the working
  alternatives (Groq via LiteLLM, OpenAI via LiteLLM, local
  faster-whisper).

## [0.3.0] — 2026-05-09

### YouTube end-to-end working
After a research pass that probed every candidate path from inside the
container, the YouTube adapter now ingests real videos with real transcripts
in real runs. ColeMedin (English) and Arnold-Oberleiter (German) channels
both deliver 10 videos per run with auto-generated captions.

### Added
- **GAP.md** — living "Konzept vs. Code" comparison, referenced from
  CLAUDE.md as the project roadmap.
- **YouTube discovery via yt-dlp** instead of the channel RSS endpoint,
  which 404/500s from data-center IPs (Docker, VPSes). Uses
  `extract_flat="in_playlist"` for a cheap newest-N fetch; relies on the
  `(source_id, external_id)` unique constraint for dedup instead of
  timestamp filtering, since the flat path doesn't expose timestamps.
- **Handle resolution via yt-dlp** — replaces the HTML-scrape path that
  hit YouTube's anti-bot wall and returned zero `UC…` IDs.
- **Tier 3 ASR pluggable** via `[asr]` config:
  - `backend = "off"` (default) — skip Tier 3, drop videos without captions
  - `backend = "litellm"` + `model = "openrouter/openai/whisper-large-v3-turbo"`
    — cloud transcription via any LiteLLM-supported provider (OpenRouter,
    Groq, OpenAI)
  - `backend = "faster-whisper"` — local CPU/GPU transcription
- **`min_duration_s` filter** is now honoured (Shorts are skipped).

### Changed
- Default `[asr] backend` is now `"off"` (was `"faster-whisper"`). Most
  channels have captions; opt in to ASR explicitly.

## [0.2.0] — 2026-05-08

### First end-to-end working release 🎉
The pipeline now produces real PDFs on real data with cloud or local LLMs.

### Fixed (proactive review pass)
- **Edition JSON schema**: `_build_edition_json()` now produces the schema
  the Typst templates actually consume (`edition_date`, `language`,
  `lead_story`, `sections[]`, `metadata.sources_count`). Previously the
  pipeline produced `date`/`stories` and rendering would have crashed
  on first try.
- **Language end-to-end**: the configured `[user] language` now flows
  into the edition JSON so templates render in the chosen language.
- **Typst ARG_MAX overflow**: large editions blew past the shell argv
  limit when the JSON was passed via `--input`. Renderer now writes
  `edition.json` and `profile.json` next to a copied template tree and
  templates read them via Typst's native `json("…")` function.
- **Robust JSON extraction**: `_extract_json()` now tries the raw text,
  ` ```json ` fences, then `{…}` and `[…]` spans in turn. Anthropic
  Sonnet's habit of wrapping JSON in fences (and sometimes returning a
  one-element list instead of an object) no longer breaks the pipeline.
- **`max_tokens` default raised to 8192** for `complete_json()` so writer
  outputs aren't truncated mid-JSON.
- **Empty SMTP early skip**: email delivery now logs a warning and skips
  itself instead of crashing when `LEMONADE_SMTP_*` env vars are missing
  but `delivery.email.enabled = true`.
- **`rmapi` pre-flight check**: friendly error before invoking subprocess
  if the binary isn't installed (instead of an opaque `FileNotFoundError`).
- **`completion_cost` failures non-fatal**: LiteLLM's pricing database
  lags new model releases, so an unknown-model lookup no longer crashes
  a successful completion.
- **Lead-story null safety** in `cover.typ` — uses `default: none`
  guards instead of dict-membership checks.

### Changed
- **Default fonts switched to DejaVu** (Serif/Sans). DejaVu ships in
  `fonts-dejavu-core`, is bundled in the Docker image, and covers
  Latin/Cyrillic/Greek with full diacritics. Source Serif 4 / Inter were
  unavailable in the slim Debian base image. Override per profile if you
  bundle other fonts via `templates/fonts/` (the runner now sets
  `TYPST_FONT_PATHS` automatically when that directory exists).
- **Dockerfile** installs `fonts-dejavu-core fonts-dejavu-extra
  fonts-noto-core` so default profiles render out of the box.

## [0.1.6] — 2026-05-08

### Added
- Docker app container can reach a host-running Ollama out of the box.
  `docker-compose.yml` sets `OLLAMA_API_BASE` to `host.docker.internal:11434`
  and adds an `extra_hosts` entry mapping `host.docker.internal` to the
  host gateway so Linux Docker behaves the same as Mac/Windows. Override
  via `OLLAMA_API_BASE` in `.env` for non-default Ollama setups.

### Fixed
- `complete_json()` no longer surfaces a confusing `JSONDecodeError` when
  the underlying LLM call fails or returns prose. It now:
  - Raises a clear "missing API key for $provider" hint when the response
    is empty.
  - Strips Markdown fences and leading/trailing prose before parsing
    (common with local models).
  - Surfaces the first 200 characters of the response on parse failure so
    `BadRequestError` etc. are no longer swallowed.

## [0.1.5] — 2026-05-08

### Fixed
- All timestamp columns are now `TIMESTAMP WITH TIME ZONE` (`TIMESTAMPTZ`).
  The model declarations missed the `timezone=True` flag, which caused
  asyncpg to reject every insert from a feed adapter with
  `can't subtract offset-naive and offset-aware datetimes`. KONZEPT.md §4
  always specified `TIMESTAMPTZ`; the implementation has caught up.
- Each source is now ingested inside its own savepoint
  (`session.begin_nested()`). A single broken feed used to poison the
  whole session — every subsequent source then failed with
  `PendingRollbackError`. Now one bad feed is just one bad feed.
- Embedding failures (e.g. missing API key for the configured embedding
  provider) no longer abort the run. The pipeline logs the error,
  commits whatever items were ingested, and continues — useful for
  diagnosing config issues without losing fetched content.
- Default `datetime` factories switched from deprecated `datetime.utcnow`
  to `datetime.now(UTC)`.

### Docs
- `config.example.toml` now warns explicitly that OpenRouter does not
  proxy embeddings, with a list of working alternatives (OpenAI, Voyage,
  Hugging Face, local Ollama).

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

[Unreleased]: https://github.com/lemonade-newspaper/lemonade/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/lemonade-newspaper/lemonade/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/lemonade-newspaper/lemonade/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.6...v0.2.0
[0.1.6]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/lemonade-newspaper/lemonade/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lemonade-newspaper/lemonade/releases/tag/v0.1.0
