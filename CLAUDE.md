# CLAUDE.md — Lemonade

## Project Overview

Lemonade generates personalized PDF newspapers from RSS feeds and YouTube channels, optimized for E-Ink tablets (reMarkable, Kindle) and general devices. Self-hosted, single-user MVP, Docker Compose deployment.

## Tech Stack

- **Language:** Python 3.12
- **CLI:** Typer
- **Database:** PostgreSQL 16 + pgvector (via SQLAlchemy async + asyncpg)
- **Migrations:** Alembic
- **LLM:** LiteLLM (provider-neutral — Anthropic, OpenAI, Ollama, Groq, etc.)
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
# Development
pip install -e ".[dev]"          # Install with dev dependencies
pytest                           # Run tests
pytest --cov=lemonade            # Run tests with coverage
ruff check .                     # Lint
ruff format .                    # Format
mypy lemonade/                   # Type check

# CLI
lemonade run                     # Full pipeline: ingest → curate → render → deliver
lemonade preview                 # Generate PDF, open preview, no delivery
lemonade sources list            # List configured sources
lemonade devices list            # List available device profiles

# Docker
docker compose up -d db          # Start Postgres
docker compose run --rm app lemonade init    # Initialize DB schema
docker compose up -d             # Start everything
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
lemonade/
├── cli.py              # Typer CLI entry point
├── config.py           # TOML loader, Pydantic models
├── db.py               # SQLAlchemy engine/session factory
├── models.py           # SQLAlchemy ORM models
├── adapters/           # Source adapters (RSS, YouTube)
├── pipeline/           # Ingest, cluster, rank, write, orchestrate
├── llm/                # LiteLLM wrapper + prompt templates
├── render/             # Typst runner + device profile loader
└── delivery/           # Delivery channels (filesystem, email, remarkable)
```
