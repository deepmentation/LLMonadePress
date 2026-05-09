# GAP.md — Konzept vs. Implementierungsstand

> Quasi-Roadmap. Vergleich der Spezifikation in [`KONZEPT.md`](KONZEPT.md) mit dem
> aktuellen Code-Stand (v0.2.0). Aktualisiert bei jedem nicht-trivialen Merge.

**Legende:** ✅ implementiert · 🟡 teilweise / mit Einschränkungen · 🔴 fehlt
komplett · ⏭️ bewusst aufgeschoben (siehe KONZEPT §11 Roadmap).

---

## §1 Vision & Scope

| Konzept-Punkt | Status | Notiz |
|---|---|---|
| Tägliches PDF aus RSS + YouTube | ✅ | End-to-end verifiziert (v0.2.0) |
| Geräte-spezifisches Rendering | ✅ | 6 Profile, Typst-Templates |
| Provider-neutral via LiteLLM | ✅ | Anthropic, OpenAI, OpenRouter, Ollama, Groq |
| reMarkable / Filesystem / E-Mail Delivery | ✅ | Alle drei Channels umgesetzt |
| Single `config.toml` | ✅ | Pydantic v2 + ENV-Override für Secrets |
| Docker Compose Deployment | ✅ | DB + App, App im `manual` Profile |

## §2 Architektur

| Konzept-Punkt | Status | Notiz |
|---|---|---|
| 5 entkoppelte Stages (Ingest → Curation → Render → Delivery) | ✅ | DB + Filesystem als Kommunikation |
| Re-runnability einzelner Stages | 🟡 | Pipeline ist atomar; Einzelstufen über CLI-Flags noch nicht freigeschaltet |
| Cron-Orchestrierung | 🟡 | Vorgesehen via Host-Cron `docker compose run …`; kein eigener Scheduler-Container |

## §3 Tech-Stack

| Komponente | Status |
|---|---|
| Python 3.12 + Typer + SQLAlchemy 2.0 async + asyncpg | ✅ |
| Postgres 16 + pgvector | ✅ |
| LiteLLM | ✅ |
| Typst | ✅ (in Docker installiert) |
| feedparser + trafilatura | ✅ |
| youtube-transcript-api + yt-dlp | ✅ (yt-dlp jetzt für Discovery + Handle-Resolution + ASR-Audio-Download) |
| faster-whisper / LiteLLM-Whisper | ✅ (konfigurierbar, beide Backends scharf) |
| aiosmtplib | ✅ |

## §4 Datenmodell

| Tabelle | Status | Notiz |
|---|---|---|
| `sources` | ✅ | |
| `items` | ✅ | inkl. `Vector(1024)` Embedding |
| `editions` | ✅ | |
| `edition_items` | ✅ | |
| `deliveries` | ✅ | |
| TIMESTAMPTZ überall | ✅ | seit v0.1.5 |

## §5 Konfigurationsformat

| Sektion | Status | Notiz |
|---|---|---|
| `[user]` | ✅ | Sprachen-Validierung gegen i18n-Registry (v0.1.1) |
| `[llm]` | ✅ | Provider-neutral; Default-Sprache `en` |
| `[asr]` | 🟡 | Felder vorhanden, Backend `litellm` für Cloud-Whisper noch nicht ausgebaut |
| `[delivery]` + Subsektionen | ✅ | |
| `[[rss]]` | ✅ | |
| `[[youtube]]` | ✅ | (Handle-Resolution war Stub bis v0.2.x) |
| `[tool.lemonade]` in `pyproject.toml` | ✅ | Single source of truth für unterstützte Sprachen |

## §6 Device-Profile

| Profil | Status |
|---|---|
| `remarkable_ppm` | ✅ |
| `remarkable_pp` | ✅ |
| `remarkable_2` | ✅ |
| `kindle_paperwhite` | ✅ |
| `ipad_mini` | ✅ |
| `generic_a5` | ✅ |
| Eine Typst-Vorlage für alle Profile | ✅ |
| Bundling im Wheel via `force-include` | ✅ |

**Fonts:** Default ist DejaVu (statt Source Serif 4 / Inter im Konzept) — DejaVu ist
in `fonts-dejavu-core` paketiert und im Container verfügbar. Source Serif 4 müsste
manuell gebundelt werden (`templates/fonts/`). Niedrige Priorität.

## §7 Stages

### 7.1 Ingestion

| Punkt | Status | Notiz |
|---|---|---|
| RSS-Adapter mit feedparser | ✅ | |
| Volltext-Nachladen via trafilatura (`follow_links`) | ✅ | |
| Per-Source Savepoints (eine kaputte Quelle kippt nicht den Run) | ✅ | seit v0.1.5 |
| YouTube Discovery | ✅ | via yt-dlp `extract_flat="in_playlist"` (Channel-RSS-Endpoint blockt aus Docker-IPs) |
| Tier 1: native Captions | ✅ | |
| Tier 2: auto-generated Captions | ✅ | |
| Tier 3: Whisper-Fallback | ✅ | konfigurierbar: LiteLLM (z.B. `openrouter/openai/whisper-large-v3-turbo`), faster-whisper (lokal), oder `off` |
| Handle-Resolution (`@channel-handle` → channel_id) | ✅ | via yt-dlp |
| `min_duration_s` Filter (Shorts ignorieren) | ✅ | |
| Whisper-Sprach-Translation | 🔴 | Konzept §7.1 erwähnt; nicht implementiert |

### 7.2 Curation & Summarization

| Punkt | Status | Notiz |
|---|---|---|
| Embeddings + pgvector KNN-Cluster (Cosine 0.85) | ✅ | |
| Repräsentant pro Cluster (längster Text) | ✅ | |
| Pass 1: Cluster-Ranking (relevance/novelty/depth) | ✅ | |
| Pass 2: Schreiben mit strukturierter JSON-Antwort | ✅ | |
| Robuste JSON-Extraktion (Fences, Array-Wrapping) | ✅ | seit v0.2.0 |
| Mehrsprachige Prompts (en/de/fr) | ✅ | seit v0.1.1 |
| Kosten-Tracking via `litellm.completion_cost` | 🟡 | Bei unbekannten Modellen Fallback auf 0.0 (v0.1.6) |

### 7.3 Rendering

| Punkt | Status | Notiz |
|---|---|---|
| Typst-Subprocess mit JSON-Inputs | ✅ | Tempfile-basiert (kein ARG_MAX-Risiko) |
| Cover, Story-Block, Colophon | ✅ | |
| Section-Gruppierung nach Kategorie | ✅ | seit v0.2.0 |
| `#outline` für reMarkable-Sidebar-Bookmarks | 🔴 | Profile haben `embed_bookmarks: true`, Template setzt es nicht um |
| Image-Embedding (gedithered Thumbnails) | 🔴 | Konzept §11 v1.1 — bewusst aufgeschoben ⏭️ |
| Hyperlink-Modi (`inline` / `short_url` / `footnote`) | 🔴 | Profile haben das Feld, Template ignoriert es |
| Pull-Quotes | 🟡 | Im LLM-Output produziert, im Template nicht gerendert |

### 7.4 Delivery

| Channel | Status |
|---|---|
| reMarkable Cloud via `rmapi` | ✅ (mit Pre-Flight-Check seit v0.2.0) |
| Filesystem | ✅ |
| E-Mail (aiosmtplib + PDF-Attachment) | ✅ (mit SMTP-Validation seit v0.2.0) |
| Send-to-Kindle Sonderfall | 🟡 | Funktioniert via E-Mail-Channel, nicht explizit getestet |
| Annotation-aware Cleanup auf reMarkable | 🔴 | Konzept §7.4.1; v1.1 Roadmap ⏭️ |

### 7.5 Delivery-Orchestrierung

| Punkt | Status |
|---|---|
| `asyncio.gather` mit `return_exceptions=True` | 🟡 | Aktuell sequentiell mit try/except pro Channel — Effekt äquivalent, aber nicht parallel |
| Per-Channel Logging | ✅ |
| `deliveries`-Tabelle mit Audit-Trail | ✅ |

## §8 Repo-Struktur

| Vorgabe | Status | Notiz |
|---|---|---|
| `lemonade/` Modul-Layout | ✅ | exakt wie spezifiziert |
| `templates/` mit Komponenten | ✅ | + `lemonade/_bundled/` für Wheel-Install |
| `device_profiles/` als YAML | ✅ | |
| `examples/config.example.toml` | ✅ | |
| `tests/` mit `fixtures/` | ✅ | 63 Tests |

## §9 Deployment

| Punkt | Status |
|---|---|
| `docker-compose.yml` mit App + DB | ✅ |
| `Dockerfile` mit Typst-Install | ✅ |
| Container ↔ Host Ollama via `host.docker.internal` | ✅ (seit v0.1.6) |
| Cron-Service im Compose | 🔴 | Bewusst entfernt — Host-Cron statt Container-Cron empfohlen |
| `lemonade init`, `lemonade rmapi-auth`, `lemonade preview` | ✅ |

## §10 CLI-Kommandos

| Kommando | Status |
|---|---|
| `lemonade run` | ✅ |
| `lemonade preview` | ✅ |
| `lemonade init` | ✅ |
| `lemonade sources list` | ✅ |
| `lemonade sources test` | 🔴 |
| `lemonade devices list` | ✅ |
| `lemonade edition show <date>` | 🔴 |
| `lemonade backfill <range>` | 🔴 |
| `lemonade costs --month` | 🔴 |
| `lemonade rmapi-auth` | 🔴 |
| `lemonade email-test` | 🟡 (Stub vorhanden, nicht ausgereift) |

## §11 Roadmap-Items (bewusst ⏭️)

| Item | Konzept-Phase | Status |
|---|---|---|
| Annotation-aware Cleanup | v1.1 | ⏭️ |
| Prefect statt Cron | v1.1 | ⏭️ |
| OPML-Import | v1.1 | ⏭️ |
| Image-Embedding | v1.1 | ⏭️ |
| HTML-Mail-Variante | v1.1 | ⏭️ |
| Plugin-System / X-Adapter | v1.2 | ⏭️ |
| Template-Gallery | v1.2 | ⏭️ |
| One-Click-Deploy | v1.2 | ⏭️ |
| MkDocs-Site | v1.2 | ⏭️ |
| Open Notebook Integration / Cross-Edition Memory | v2.0 | ⏭️ |

## §12 Bewusste Trade-offs (KONZEPT.md §12)

Alle wie im Konzept festgelegt. Eine Abweichung: Default-Fonts sind DejaVu statt
Source Serif 4 / Inter, aus Container-Verfügbarkeitsgründen. Profile sind
trivial überschreibbar.

## §13 Risiken & Mitigations

Alle im Konzept dokumentierten Risiken bestehen weiter. Konkrete Lessons aus
v0.1.x:

- LiteLLM-Pricing-DB lagging → bereits abgefangen (v0.1.6).
- Anthropic Credit-Balance-Out → klare Fehlermeldung wird durchgereicht.
- Lokale LLMs / JSON-Output → mehrstufige JSON-Extraktion erschlägt das.

---

## Aktuelle Prioritäten

1. **Pull-Quotes & Bookmarks im Typst-Template** — kleiner Layout-Win.
2. **Hyperlink-Modi im Template** (`inline` / `short_url` / `footnote`).
3. **Per-Stage-CLI** (`lemonade ingest`, `cluster`, `render` …) — bessere Debug-UX.
4. **`lemonade edition show <date>` + `lemonade costs --month`** — fehlende Inspektion.
5. **Annotation-aware Cleanup** auf reMarkable (KONZEPT v1.1).
