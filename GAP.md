# GAP.md — Konzept vs. Implementierungsstand

> Quasi-Roadmap. Vergleich der Spezifikation in [`KONZEPT.md`](KONZEPT.md) mit dem
> aktuellen Code-Stand (**v0.7.1**, 84 Tests). Aktualisiert bei jedem
> nicht-trivialen Merge.

**Legende:** ✅ implementiert · 🟡 teilweise / mit Einschränkungen · 🔴 fehlt
komplett · ⏭️ bewusst aufgeschoben (siehe KONZEPT §11 Roadmap).

---

## §1 Vision & Scope

| Konzept-Punkt | Status | Notiz |
|---|---|---|
| Tägliches PDF aus RSS + YouTube | ✅ | End-to-end produktiv im Einsatz |
| Geräte-spezifisches Rendering | ✅ | 6 Profile, Typst-Templates |
| Provider-neutral via LiteLLM | ✅ | Anthropic, OpenAI, OpenRouter, Ollama, Groq |
| reMarkable / Filesystem / E-Mail Delivery | ✅ | Alle drei Channels umgesetzt |
| Single `config.toml` | ✅ | Pydantic v2 + ENV-Override für Secrets |
| Docker Compose Deployment | ✅ | DB + App, App im `manual` Profile |

## §2 Architektur

| Konzept-Punkt | Status | Notiz |
|---|---|---|
| 5 entkoppelte Stages (Ingest → Curation → Render → Delivery) | ✅ | DB + Filesystem als Kommunikation |
| Re-runnability einzelner Stages | 🟡 | Pipeline ist atomar; Einzelstufen-CLI noch nicht freigeschaltet |
| Cron-Orchestrierung | 🟡 | Vorgesehen via Host-Cron `docker compose run …`; kein eigener Scheduler-Container |

## §3 Tech-Stack

| Komponente | Status |
|---|---|
| Python 3.12 + Typer + SQLAlchemy 2.0 async + asyncpg | ✅ |
| Postgres 16 + pgvector | ✅ |
| LiteLLM | ✅ |
| Typst | ✅ (in Docker installiert, Tempfile-basierter Runner) |
| feedparser + trafilatura | ✅ |
| youtube-transcript-api + yt-dlp | ✅ (yt-dlp für Discovery, Handle-Resolution, Audio-Download) |
| faster-whisper / LiteLLM-Whisper | ✅ (3 ASR-Backends: `off` / `litellm` / `faster-whisper`) |
| ffmpeg | ✅ (für Audio-Kompression vor ASR-Upload, v0.3.2) |
| json-repair | ✅ (für robuste LLM-JSON-Extraktion, v0.6.x) |
| aiosmtplib | ✅ |

## §4 Datenmodell

| Tabelle | Status | Notiz |
|---|---|---|
| `sources` | ✅ | |
| `items` | ✅ | inkl. `Vector(1024)` Embedding |
| `editions` | ✅ | inkl. `metrics` JSONB für Pipeline-Counts + Ranker-Scores |
| `edition_items` | ✅ | mit `cluster_id` + `rank` |
| `deliveries` | ✅ | Audit-Trail pro Channel |
| TIMESTAMPTZ überall | ✅ | seit v0.1.5 |

## §5 Konfigurationsformat

| Sektion | Status | Notiz |
|---|---|---|
| `[user]` | ✅ | Sprachen-Validierung gegen i18n-Registry (v0.1.1) |
| `[llm]` | ✅ | Provider-neutral; Default-Sprache `en` |
| `[asr]` | ✅ | Backends: `off` (default), `litellm` (mit OpenRouter-Direct-REST), `faster-whisper` |
| `[render]` (qr_codes) | ✅ | seit v0.7.1 — Layout-Optionen die nicht device-spezifisch sind |
| `[delivery]` + Subsektionen | ✅ | filesystem aktiv, email + remarkable opt-in |
| `[[rss]]` | ✅ | inkl. `follow_links` für Volltext-Nachladen |
| `[[youtube]]` | ✅ | Channel-ID oder `@handle`, `min_duration_s` honoriert |
| `[tool.llmonadepress]` in `pyproject.toml` | ✅ | Single source of truth für unterstützte Sprachen |

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
| Per-Source Savepoints (kaputte Quelle kippt nicht den Run) | ✅ | seit v0.1.5 |
| YouTube Discovery | ✅ | via yt-dlp `extract_flat="in_playlist"` (Channel-RSS-Endpoint blockt aus Docker-IPs) |
| Tier 1: native Captions | ✅ | youtube-transcript-api |
| Tier 2: auto-generated Captions | ✅ | youtube-transcript-api |
| Tier 3: ASR-Fallback | ✅ | OpenRouter (Direct-REST, base64-JSON), Groq/OpenAI (LiteLLM), faster-whisper (lokal), `off`. Audio mit ffmpeg auf mono opus 24 kbps komprimiert (Whisper-Cap 25 MB). |
| Handle-Resolution (`@channel-handle` → channel_id) | ✅ | via yt-dlp |
| `min_duration_s` Filter (Shorts ignorieren) | ✅ | seit v0.3.0 |
| Whisper-Sprach-Translation | 🔴 | Konzept §7.1 erwähnt; nicht implementiert |

### 7.2 Curation & Summarization

| Punkt | Status | Notiz |
|---|---|---|
| Embeddings + pgvector KNN-Cluster (Cosine 0.85) | ✅ | |
| Repräsentant pro Cluster (längster Text) | ✅ | |
| Cross-Edition Dedup ("nicht nochmal publizieren") | ✅ | seit v0.4.0 — SQL `NOT IN (SELECT item_id FROM edition_items …)` |
| Pass 1: Cluster-Ranking (relevance/novelty/depth/breadth) | ✅ | breadth-Signal seit v0.4.0 |
| Authoritative Sources statt LLM-Hallucination | ✅ | seit v0.4.0 — Item × Source Join nach Cluster |
| Pass 2: Schreiben mit strukturierter JSON-Antwort | ✅ | |
| Validation + Retry-Loop (Headline ≥ 8, Body ≥ 80 chars, max 3 Versuche) | ✅ | seit v0.5.0 |
| Robuste JSON-Extraktion | ✅ | Multi-Candidate, Dict-Präferenz (v0.6.1), json-repair für unescaped quotes (v0.6.2) |
| Mehrsprachige Prompts (en/de/fr) | ✅ | seit v0.1.1 |
| Kosten-Tracking via `litellm.completion_cost` | 🟡 | Bei unbekannten Modellen Fallback auf 0.0 (v0.1.6) |

### 7.3 Rendering

| Punkt | Status | Notiz |
|---|---|---|
| Typst-Subprocess mit JSON-Inputs | ✅ | Tempfile-basiert (kein ARG_MAX-Risiko) |
| Cover, Story-Block, Colophon | ✅ | |
| Section-Gruppierung nach Kategorie | ✅ | seit v0.2.0 |
| Authoritative Source-Zeilen mit Channel + Datum + Title | ✅ | seit v0.4.0 |
| Pull-Quotes im Layout | ✅ | seit v0.4.0 (`story.typ`) |
| Page-Break pro Artikel (kein Bleed in nächste Story) | ✅ | seit v0.7.0 |
| QR-Code pro Source-URL | ✅ | seit v0.7.0 — `qrcode[pil]`, 60/10/30 Layout. Opt-out via `[render] qr_codes = false` (v0.7.1) |
| `#outline` für reMarkable-Sidebar-Bookmarks | 🔴 | Profile haben `embed_bookmarks: true`, Template setzt es nicht um |
| Image-Embedding (gedithered Thumbnails) | 🔴 | Konzept §11 v1.1 — bewusst aufgeschoben ⏭️ |
| Hyperlink-Modi (`inline` / `short_url` / `footnote`) | 🔴 | Profile haben das Feld, Template ignoriert es |

### 7.4 Delivery

| Channel | Status |
|---|---|
| reMarkable Cloud via `rmapi` | ✅ (mit Pre-Flight-Check seit v0.2.0) |
| Filesystem | ✅ (mit Same-File-No-op seit v0.6.2) |
| E-Mail (aiosmtplib + PDF-Attachment) | ✅ (mit SMTP-Validation seit v0.2.0) |
| Send-to-Kindle Sonderfall | 🟡 | Funktioniert via E-Mail-Channel, nicht explizit getestet |
| Annotation-aware Cleanup auf reMarkable | 🔴 | Konzept §7.4.1; v1.1 Roadmap ⏭️ |

### 7.5 Delivery-Orchestrierung & Observability

| Punkt | Status | Notiz |
|---|---|---|
| `asyncio.gather` mit `return_exceptions=True` | 🟡 | Aktuell sequentiell mit try/except pro Channel — Effekt äquivalent, aber nicht parallel |
| Per-Channel Logging | ✅ | |
| `deliveries`-Tabelle mit Audit-Trail | ✅ | |
| Pipeline-Stage-Summaries (INFO-Logs) | ✅ | seit v0.6.0 — eligible items, cluster sizes, ranker scores, written/dropped |
| `edition.metrics` mit Stage-Counts + Ranker-Scores | ✅ | seit v0.6.0 |
| `LEMONADE_LOG_LEVEL` ENV-Var für Tuning | ✅ | Default INFO; LiteLLM auf WARNING gepinnt |

## §8 Repo-Struktur

| Vorgabe | Status | Notiz |
|---|---|---|
| `llmonadepress/` Modul-Layout | ✅ | umbenannt aus `lemonade/` in v0.5.0 (CLI-Kommando bleibt `lemonade`) |
| `templates/` mit Komponenten | ✅ | + `llmonadepress/_bundled/` für Wheel-Install |
| `device_profiles/` als YAML | ✅ | |
| `examples/config.example.toml` | ✅ | |
| `tests/` mit `fixtures/` | ✅ | 78 Tests |

## §9 Deployment

| Punkt | Status |
|---|---|
| `docker-compose.yml` mit App + DB | ✅ |
| `Dockerfile` mit Typst + ffmpeg + Fonts | ✅ |
| Container ↔ Host Ollama via `host.docker.internal` | ✅ (seit v0.1.6) |
| Cron-Service im Compose | 🔴 | Bewusst entfernt — Host-Cron statt Container-Cron empfohlen |
| `lemonade init`, `lemonade preview`, `lemonade run` | ✅ |

## §10 CLI-Kommandos

| Kommando | Status | Notiz |
|---|---|---|
| `lemonade run` | ✅ | |
| `lemonade preview` | ✅ | |
| `lemonade init` | ✅ | |
| `lemonade sources list` | ✅ | |
| `lemonade sources test` | 🔴 | |
| `lemonade devices list` | ✅ | |
| `lemonade edition show <date>` | ✅ | seit v0.6.0 — Pipeline-Counts, Ranker-Scores, Items, gelieferte Stories |
| `lemonade backfill <range>` | 🔴 | |
| `lemonade costs --month` | 🔴 | |
| `lemonade rmapi-auth` | 🔴 | aktuell `rmapi` direkt im Container nutzen |
| `lemonade email-test` | 🟡 | funktioniert, aber wenig getestet |

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

Ein Branding-Detail: das Modul heißt seit v0.5.0 `llmonadepress`, das
CLI-Kommando und die ENV-Vars (`LEMONADE_*`) sowie der Postgres-Role-Name
bleiben aber `lemonade` für Operations-Komfort und Backwards-Compat.

## §13 Risiken & Mitigations

Alle im Konzept dokumentierten Risiken bestehen weiter. Lessons aus v0.1.x – v0.6.x:

- **LiteLLM-Pricing-DB lagging** → bereits abgefangen (v0.1.6), unbekannte Modelle → Cost = 0.
- **Anthropic Credit-Balance-Out** → klare Fehlermeldung wird durchgereicht (v0.1.6).
- **LLM-JSON-Output mit unescaped Quotes** → mehrstufige Extraktion + json-repair als Fallback (v0.6.x).
- **Inner-Array masquerading als Article** → Dict-Präferenz im Extraktor + Shape-validierter Unwrap im Writer (v0.6.1).
- **YouTube-Channel-RSS aus Docker-IPs blockiert** → Discovery über yt-dlp (v0.3.0).
- **Whisper 25 MB Upload-Cap** → Audio-Kompression mit ffmpeg (v0.3.2).
- **OpenRouter Audio-API ist nicht OpenAI-kompatibel** → eigener Direct-REST-Pfad mit base64-JSON (v0.3.1).
- **Filesystem-Delivery copy-on-self** → Same-File-Detection (v0.6.2).

---

## Aktuelle Prioritäten

1. **Pull-Quotes-Layout polish + Bookmarks im Typst-Template** — `#outline` für
   reMarkable-Sidebar-Navigation; Pull-Quotes sind gerendert, aber das visuelle
   Setup (Größe, Position, Farbe) verträgt mehr Liebe.
2. **Hyperlink-Modi im Template** (`inline` / `short_url` / `footnote`) — Profile
   exponieren das Feld, das Template ignoriert es.
3. **Per-Stage-CLI** (`lemonade ingest`, `cluster`, `render` …) — bessere Debug-UX
   für Entwicklung und Fehlersuche.
4. **`lemonade backfill <range>` + `lemonade costs --month`** — fehlende
   Inspektion / Bulk-Operationen aus KONZEPT §10.
5. **Annotation-aware Cleanup** auf reMarkable (KONZEPT v1.1).
