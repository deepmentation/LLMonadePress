# 🍋 LLMonadePress

> **Wenn das Leben dir 800 RSS-Items und 30 Stunden YouTube schenkt, macht LLMonadePress dir eine 8-seitige Zeitung daraus.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

🇬🇧 **[English version](README.md)**

---

## Was ist LLMonadePress?

LLMonadePress ist ein selbst-gehosteter, KI-gestützter Daily-Newspaper-Generator. Er liest deine RSS-Feeds und YouTube-Kanäle, clustert und priorisiert Stories per LLM und rendert geräteoptimierte PDFs für E-Ink-Tablets wie das reMarkable oder Kindle Paperwhite. LLM-Provider-neutral via LiteLLM — nutze Anthropic, OpenAI, Ollama, Groq, OpenRouter oder einen anderen unterstützten Anbieter.

## Features

- **RSS + YouTube als Quellen** — beliebige RSS/Atom-Feeds oder YouTube-Kanäle abonnieren
- **3-stufiger YouTube-Transcript-Fallback** — native Captions → Auto-Captions → Whisper (lokal oder Cloud)
- **LLM-gestützte Kuration** — Clustering, Ranking und Artikelschreiben via [LiteLLM](https://github.com/BerriAI/litellm) (Anthropic, OpenAI, Ollama, Groq, OpenRouter und mehr)
- **Geräteoptimierte PDFs** — gerendert mit [Typst](https://typst.app/), zugeschnitten auf Bildschirmgröße, Margins und Typografie
- **6 Geräteprofile** — reMarkable Paper Pro Move, Paper Pro, reMarkable 2, Kindle Paperwhite, iPad mini, generisches A5
- **3 Zustellkanäle** — reMarkable Cloud (via rmapi), Filesystem (Syncthing/Dropbox/USB), E-Mail (mit Send-to-Kindle-Support)
- **Eine `config.toml`** — eine Datei für Quellen, LLM-Provider, Zustellung und Gerät
- **Docker-Compose-Deployment** — Postgres + pgvector inklusive, läuft auf jedem VPS

## Unterstützte Geräte

| Profil-ID | Gerät | Display | Notizen |
|---|---|---|---|
| `remarkable_ppm` | reMarkable Paper Pro Move | 107,8 × 195,6 mm | Color, 264 ppi |
| `remarkable_pp` | reMarkable Paper Pro 11.8" | 196 × 261 mm | Color, 229 ppi |
| `remarkable_2` | reMarkable 2 | 157 × 209 mm | Mono, 226 ppi |
| `kindle_paperwhite` | Kindle Paperwhite (12. Gen) | 91 × 122 mm | Mono, 300 ppi |
| `ipad_mini` | iPad mini 8.3" | 134,8 × 195,4 mm | Color, 326 ppi |
| `generic_a5` | DIN A5 | 148 × 210 mm | Vektor, geräteneutral, druckbar |

Geräteprofile sind YAML-Dateien — Community-Beiträge für neue Geräte sind willkommen!

## Schnellstart

**1. Repository klonen**

```bash
git clone https://github.com/deepmentation/LLMonadePress.git
cd LLMonadePress
```

**2. Environment und Config einrichten**

Beide Dateien müssen *vor* dem Docker-Start auf der Festplatte existieren —
sonst legt Dockers Bind-Mount sie stillschweigend als leere Verzeichnisse an.

```bash
cp .env.example .env
cp examples/config.example.toml config.toml
```

`.env` editieren und LLM-API-Keys eintragen, `config.toml` editieren und
deine RSS-Feeds + YouTube-Kanäle hinzufügen.

**3. Datenbank starten**

Der App-Container ist ein Batch-Job, kein Daemon — also läuft im Hintergrund
nur die Datenbank.

```bash
docker compose up -d db
```

**4. Schema initialisieren**

```bash
docker compose run --rm app init
```

**5. Eine Test-Edition vorschauen (ohne Zustellung)**

```bash
docker compose run --rm app preview
```

**6. Vollständige Edition mit Zustellung**

```bash
docker compose run --rm app run
```

> **Cron / Scheduling:** ruf `docker compose run --rm app run` aus einem
> Host-Cronjob (oder systemd-Timer) zur gewünschten Zeit auf. LLMonadePress
> ist zwischen Runs zustandslos — der State liegt komplett in Postgres.

## Konfiguration

Die komplette Konfiguration steckt in einer einzigen `config.toml`. Siehe
[`examples/config.example.toml`](examples/config.example.toml) für ein
vollständig kommentiertes Beispiel.

Wichtige Sektionen:

| Sektion | Zweck |
|---|---|
| `[user]` | Sprache, Ausgabezeit, Story-Anzahl |
| `[llm]` | LiteLLM-Provider, Modelle, API-Key-Quelle |
| `[asr]` | Whisper-Einstellungen für YouTube-Fallback |
| `[delivery]` | reMarkable Cloud, Filesystem-Pfad, E-Mail/SMTP |
| `[[rss]]` | RSS/Atom-Feed-Abonnements |
| `[[youtube]]` | YouTube-Kanal-Abonnements |

## Architektur

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

Fünf entkoppelte Stages, die über Datenbank und Dateisystem kommunizieren. Jede Stage ist unabhängig wiederholbar.

## Entwicklung

```bash
# Editable-Install mit Dev-Dependencies
pip install -e ".[dev]"

# Tests ausführen
pytest

# Lint und Format
ruff check .
ruff format .

# Type-Checking
mypy llmonadepress
```

## Mitmachen

Beiträge sind willkommen — Bug-Fixes, neue Geräteprofile, Zustellkanäle, Übersetzungen oder Feature-Ideen. Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Workflow, Code-Stil und Good-First-Issues.

## Über uns

[**deepmentation**](https://deepmentation.ai) sind Experten für die Nutzung von KI, LLMs und KI-Tools. Mit LLMonadePress versorgen wir uns selbst täglich mit News aus unseren vielen Quellen. Nutze LLMonadePress für dein persönliches Daily Update — oder hilf uns, diese Idee weiterzuentwickeln.

## Lizenz

[MIT](https://opensource.org/licenses/MIT)
