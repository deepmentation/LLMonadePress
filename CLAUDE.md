# CLAUDE.md — LLMonadePress

## Roadmap & Concept Gap

**[`GAP.md`](GAP.md) is the living roadmap.** It maps every section of
[`KONZEPT.md`](KONZEPT.md) to current implementation status (✅ / 🟡 / 🔴 / ⏭️)
and lists active priorities. Update GAP.md whenever a non-trivial feature
lands or a new gap is discovered — it is the single source of truth for
"what's done, what's next."

## Project Overview

LLMonadePress generates personalized PDF newspapers from RSS feeds and YouTube channels, optimized for E-Ink tablets (reMarkable, Kindle) and general devices. Self-hosted, single-user MVP, Docker Compose deployment.

## Tech Stack

- **Language:** Python 3.12
- **CLI:** Typer
- **Database:** PostgreSQL 16 + pgvector (via SQLAlchemy async + asyncpg)
- **Migrations:** Alembic
- **LLM:** LiteLLM (provider-neutral — Anthropic, OpenAI, Ollama, Groq, OpenRouter, etc.)
- **PDF Rendering:** Typst (templates + device profiles as JSON/YAML inputs)
- **RSS:** feedparser + trafilatura (fulltext extraction)
- **YouTube:** youtube-transcript-api + yt-dlp + faster-whisper (3-tier transcript fallback)
- **Email:** aiosmtplib
- **Container:** Docker + Compose

## Architecture

Five decoupled pipeline stages, communicating via DB + filesystem:

```
Sources (TOML) → Ingestion (Adapters) → Curation (LiteLLM) → Render (Typst) → Delivery (rmapi/fs/email)
                        ↓                      ↓                    ↓
                  Postgres + pgvector         PDFs            rmapi / fs / email
```

Each stage is independently re-runnable. Orchestrated by Cron (MVP).

## Commands

```bash
# Development (runs against local Python, not Docker)
pip install -e ".[dev]"             # Install with dev dependencies
pytest                              # Run tests (78 currently)
pytest --cov=llmonadepress          # Run tests with coverage
ruff check .                        # Lint
ruff format .                       # Format
mypy llmonadepress                  # Type check

# CLI (inside or outside Docker — entry point is `lemonade`)
lemonade run                        # Full pipeline: ingest → curate → render → deliver
lemonade preview                    # Generate PDF, no delivery
lemonade init                       # Create DB schema + pgvector extension
lemonade sources list               # List configured sources
lemonade devices list               # List available device profiles
lemonade edition show <YYYY-MM-DD>  # Inspect a past edition (counts, scores, items)
lemonade email-test                 # Send a test email via configured SMTP

# Docker (the canonical operator path — config.toml + .env stay on host)
docker compose up -d db             # Start Postgres only (app is a batch job)
docker compose run --rm app init    # Initialize DB schema
docker compose run --rm app preview # Render a PDF without delivering
docker compose run --rm app run     # Full edition with delivery
```

## Key Design Decisions

- **Structured JSON between stages.** LLM outputs JSON (headline, deck, body, sources). Typst reads JSON. Decoupled: change template without re-running LLM.
- **Device profiles are YAML.** Community can add profiles via PR. One Typst template, all devices.
- **LiteLLM for provider neutrality.** User picks their LLM in config.toml. No vendor lock-in.
- **Postgres over SQLite.** pgvector for embeddings in the same store. Multi-user path is trivial later.
- **Typst over LaTeX.** Lower barrier for community templates. Single binary, no texlive.

## Code Conventions

- Python 3.12, type hints everywhere, `Mapped`/`mapped_column` for SQLAlchemy
- Async by default (asyncpg, aiosmtplib, async adapters)
- Ruff for linting + formatting (line length 99)
- Pydantic v2 for config and validation
- Tests with pytest-asyncio, fixtures in tests/fixtures/
- Commit messages: conventional commits (feat:, fix:, chore:, docs:)
- No comments unless the WHY is non-obvious

## Config

Single `config.toml` per user. Secrets via ENV variables (never in TOML).
See `examples/config.example.toml` for full reference.

## File Layout

```
llmonadepress/             # Python package (renamed from `lemonade/` in v0.5.0;
                           # CLI command, ENV vars, Postgres role keep `lemonade`)
├── cli.py                 # Typer CLI entry point (`lemonade …`)
├── config.py              # TOML loader, Pydantic models (LLMonadePressConfig)
├── db.py                  # SQLAlchemy async engine/session factory
├── models.py              # SQLAlchemy ORM models
├── _paths.py              # bundled-vs-repo data path resolver
├── adapters/              # Source adapters (RSS, YouTube via yt-dlp)
├── pipeline/              # ingest, cluster, rank, write, orchestrate
├── llm/                   # LiteLLM wrapper + multilingual prompt templates
├── render/                # Typst runner + device profile loader
└── delivery/              # filesystem, email, remarkable
```

## Naming convention (intentional, see GAP §12)

| Surface | Name |
|---|---|
| Display name / brand | `LLMonadePress` |
| Python package / module / PyPI | `llmonadepress` |
| CLI command, ENV var prefix (`LEMONADE_*`), Postgres role | `lemonade` |
