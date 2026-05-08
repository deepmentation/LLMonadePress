# 🍋 Lemonade

> **When life gives you 800 RSS items and 30 hours of YouTube, Lemonade makes you an 8-page newspaper.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

---

## What is Lemonade?

Lemonade is a self-hosted, AI-powered daily newspaper generator. It pulls content from your RSS feeds and YouTube channels, clusters and ranks stories with an LLM, and renders device-optimized PDFs for E-Ink tablets like the reMarkable or Kindle Paperwhite. It is LLM-provider-neutral via LiteLLM — use Anthropic, OpenAI, Ollama, Groq, OpenRouter, or any other supported provider.

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

```bash
# 1. Clone the repository
git clone https://github.com/lemonade-newspaper/lemonade.git
cd lemonade

# 2. Set up environment and config (BOTH files must exist before `docker compose up`,
#    otherwise Docker's bind mount auto-creates them as empty directories).
cp .env.example .env                          # add your API keys here
cp examples/config.example.toml config.toml   # edit your sources & preferences

# 3. Start the database (the app container is a batch job, not a daemon)
docker compose up -d db

# 4. Initialize the schema
docker compose run --rm app init

# 5. Preview a test edition (no delivery)
docker compose run --rm app preview

# 6. Run a full edition with delivery
docker compose run --rm app run
```

> **Cron / scheduling:** call `docker compose run --rm app run` from a host
> cron job (or systemd timer) at your desired time. Lemonade itself is
> stateless between runs — all state lives in Postgres.

## Configuration

All configuration lives in a single `config.toml`. See [`examples/config.example.toml`](examples/config.example.toml) for a fully commented example.

Key sections:

| Section | Purpose |
|---|---|
| `[user]` | Name, device profile, language |
| `[llm]` | LiteLLM provider, model, API key reference |
| `[asr]` | Whisper settings for YouTube fallback |
| `[delivery]` | reMarkable Cloud, filesystem path, email/SMTP |
| `[[rss]]` | RSS/Atom feed subscriptions |
| `[[youtube]]` | YouTube channel subscriptions |

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
mypy lemonade
```

## Contributing

Contributions are welcome! Whether it is a bug fix, a new device profile, or a feature idea — feel free to open an [issue](https://github.com/lemonade-newspaper/lemonade/issues) or submit a pull request.

Good first contributions:

- Add a new device profile (just a YAML file + a test)
- Improve Typst templates
- Add a new delivery channel
- Add a translation

## License

[MIT](https://opensource.org/licenses/MIT)
