# 🍋 LLMonadePress

> **When life gives you 800 RSS items and 30 hours of YouTube, LLMonadePress makes you an 8-page newspaper.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

🇩🇪 **[Deutsche Version](README_DE.md)**

---

## What is LLMonadePress?

LLMonadePress is a self-hosted, AI-powered daily newspaper generator. It pulls content from your RSS feeds and YouTube channels, clusters and ranks stories with an LLM, and renders device-optimized PDFs for E-Ink tablets like the reMarkable or Kindle Paperwhite. It is LLM-provider-neutral via LiteLLM — use Anthropic, OpenAI, Ollama, Groq, OpenRouter, or any other supported provider.

## Features

- **RSS + YouTube sources** — subscribe to any RSS/Atom feed or YouTube channel
- **3-tier YouTube transcript fallback** — native captions → auto-generated captions → Whisper ASR (local or cloud)
- **LLM-powered curation** — clustering, ranking, and article writing via [LiteLLM](https://github.com/BerriAI/litellm) (Anthropic, OpenAI, Ollama, Groq, OpenRouter, and more)
- **Device-optimized PDFs** — rendered with [Typst](https://typst.app/), tailored to each screen's dimensions, margins, and typography
- **6 device profiles** — reMarkable Paper Pro Move, Paper Pro, reMarkable 2, Kindle Paperwhite, iPad mini, generic A5
- **3 delivery channels** — reMarkable Cloud (via rmapi), filesystem (Syncthing/Dropbox/USB), email (with Send-to-Kindle support)
- **Single `config.toml`** — one file configures sources, LLM provider, delivery, and device
- **Docker Compose deployment** — Postgres + pgvector included, runs on any VPS

## Supported Devices

| Profile ID | Device | Display | Notes |
|---|---|---|---|
| `remarkable_ppm` | reMarkable Paper Pro Move | 107.8 × 195.6 mm | Color, 264 ppi |
| `remarkable_pp` | reMarkable Paper Pro 11.8" | 196 × 261 mm | Color, 229 ppi |
| `remarkable_2` | reMarkable 2 | 157 × 209 mm | Mono, 226 ppi |
| `kindle_paperwhite` | Kindle Paperwhite (12th Gen) | 91 × 122 mm | Mono, 300 ppi |
| `ipad_mini` | iPad mini 8.3" | 134.8 × 195.4 mm | Color, 326 ppi |
| `generic_a5` | DIN A5 | 148 × 210 mm | Vector, device-neutral, printable |

Device profiles are YAML files — community contributions for new devices are welcome!

## Quick Start

**1. Clone the repository**

```bash
git clone https://github.com/deepmentation/LLMonadePress.git
cd LLMonadePress
```

**2. Set up environment and config**

Both files must exist on disk *before* you start Docker — otherwise Docker's
bind mount silently creates them as empty directories.

```bash
cp .env.example .env
cp examples/config.example.toml config.toml
```

Edit `.env` to add your LLM API keys, and `config.toml` to add your RSS feeds
and YouTube channels.

**3. Start the database**

The app container is a batch job, not a daemon, so only the database runs in
the background.

```bash
docker compose up -d db
```

**4. Initialize the schema**

```bash
docker compose run --rm app init
```

**5. Preview a test edition (no delivery)**

```bash
docker compose run --rm app preview
```

**6. Run a full edition with delivery**

```bash
docker compose run --rm app run
```

> **Cron / scheduling:** call `docker compose run --rm app run` from a host
> cron job (or systemd timer) at your desired time. LLMonadePress itself is
> stateless between runs — all state lives in Postgres.

## Configuration

All configuration lives in a single `config.toml`. See [`examples/config.example.toml`](examples/config.example.toml) for a fully commented example.

Key sections:

| Section | Purpose |
|---|---|
| `[user]` | Output language, timezone, delivery time, max stories per edition |
| `[llm]` | LiteLLM provider strings for ranker, writer, embedding model |
| `[asr]` | Tier-3 ASR backend for YouTube videos without captions (`off` / `litellm` / `faster-whisper`) |
| `[delivery]` | Which device profiles to render, plus filesystem / email / reMarkable channel settings |
| `[[rss]]` | RSS/Atom feed subscriptions (URL + category, optional `follow_links` for full text) |
| `[[youtube]]` | YouTube channel subscriptions (channel ID or `@handle`, `min_duration_s` to skip Shorts) |

Secrets (API keys, SMTP password) live in environment variables (`.env`),
never in `config.toml`.

## Architecture

```
┌──────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────┐   ┌──────────┐
│ Sources  │──▶│ Ingestion  │──▶│ Curation +   │──▶│ Render   │──▶│ Delivery │
│ Config   │   │ (Adapters) │   │ Summarization│   │ (per     │   │ (per     │
│ TOML     │   │            │   │ (LiteLLM)    │   │ Device)  │   │ Channel) │
└──────────┘   └─────┬──────┘   └──────┬───────┘   └────┬─────┘   └─────┬────┘
                     ▼                 ▼                ▼               ▼
                 ┌───────────────────────────────┐  ┌──────┐    ┌──────────────┐
                 │ Postgres + pgvector           │  │ PDFs │    │ rmapi / file │
                 │ (items, clusters, editions)   │  │      │    │ /  email     │
                 └───────────────────────────────┘  └──────┘    └──────────────┘
```

Five decoupled stages communicating via database and filesystem. Each stage is independently re-runnable.

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type checking
mypy llmonadepress
```

## Contributing

Contributions are welcome — bug fixes, new device profiles, delivery channels, translations, or feature ideas. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, code style, and good first issues.

## About

[**deepmentation**](https://deepmentation.ai) are experts in applied AI, LLMs, and AI tooling. We use LLMonadePress ourselves to keep up with our many news sources every day. Use it for your own daily briefing — or help us evolve the idea further.

## License

[MIT](https://opensource.org/licenses/MIT)
