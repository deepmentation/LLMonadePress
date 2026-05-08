# Lemonade — Technisches Konzept (MVP)

> **When life gives you 800 RSS items and 30 hours of YouTube, Lemonade makes you an 8-page newspaper.**
>
> Ein selbst-gehosteter, AI-gestützter Daily-Newspaper-Generator für E-Ink-Tablets und Tablets allgemein. Open-Source, deviceneutral, LLM-providerneutral.

**Status:** Konzept v0.1 — Mai 2026
**Initial-Zielplattform:** reMarkable Paper Pro Move (mit Generic-PDF-Fallback)
**Lizenz:** MIT
**Code-Name:** `lemonade`

---

## 1. Vision & Scope

Lemonade generiert ein- bis zweimal täglich eine personalisierte PDF-„Zeitung" aus den vom User definierten YouTube-Kanälen und RSS-Feeds. Die PDF wird gerätespezifisch gerendert (Seitengröße, Typografie, Margins, Farbprofil) und an das Endgerät zugestellt — initial reMarkable, generisch-PDF und E-Mail.

### Was im MVP drin ist

- **Quellen:** YouTube-Kanäle (Channel-RSS + Transkript-Pipeline) und RSS/Atom-Feeds.
- **Verarbeitung:** Native Captions oder Whisper-Fallback; LLM-basiertes Clustering, Ranking, Schreiben.
- **Rendering:** PDFs für eine kuratierte Liste populärer Geräte. Set siehe §6.
- **Delivery:** reMarkable via `rmapi`, Filesystem (für Syncthing/Dropbox/USB), **E-Mail** (mit PDF-Attachment, optional Send-to-Kindle-tauglich).
- **LLM:** Provider-neutral via LiteLLM — User wählt zwischen lokal (Ollama, LM Studio) und Cloud (Anthropic, OpenAI, Gemini, Groq, …).
- **Konfiguration:** Eine `config.toml` pro User. Keine Web-UI im MVP.
- **Deployment:** Docker Compose, Single-User.

### Was bewusst NICHT im MVP ist

- X/Twitter-Adapter (zu fragil, später als Plugin).
- Themen-Discovery via Web-Search (Google News RSS reicht falls überhaupt).
- Web-UI / Multi-User / OIDC.
- Annotation-Sync rückwärts vom RM.
- NotebookLM-artige interaktive Q&A. Siehe §11.

---

## 2. Architektur-Überblick

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

Fünf strikt entkoppelte Stages, Kommunikation über DB und Files (nicht In-Memory). Jede Stage einzeln re-runnable. Orchestriert von Cron im MVP, später Prefect.

---

## 3. Tech-Stack

| Layer | Wahl | Begründung |
|---|---|---|
| Sprache | Python 3.12 | Bestes Ökosystem für RSS, YouTube, ML, PDF |
| API/CLI | Typer (CLI), FastAPI (vorbereitet) | CLI reicht für MVP |
| DB | Postgres 16 + pgvector | Embeddings im selben Store |
| LLM-Abstraktion | [LiteLLM](https://github.com/BerriAI/litellm) | Eine API für alle Provider inkl. Ollama |
| Workflow | Cron (MVP) → Prefect (v1.1) | Komplexität schrittweise einführen |
| PDF-Rendering | [Typst](https://typst.app/) | Saubere Templates, scriptbar, single binary |
| HTML→Text Fallback | trafilatura | Volltext-Extraktion aus RSS-Teasern |
| YouTube-Captions | youtube-transcript-api + yt-dlp Fallback | Doppelte Sicherheit |
| ASR | faster-whisper (lokal) / Groq (Cloud) | GPU-optional, Provider austauschbar |
| reMarkable-Push | [`rmapi` (ddvk-Fork)](https://github.com/ddvk/rmapi) | Aktivste Pflege, neuestes Sync-Protokoll |
| E-Mail-Versand | aiosmtplib | Async-SMTP, sauber |
| Container | Docker + Compose | Standard, läuft auf jedem vServer |

---

## 4. Datenmodell

```sql
-- Source-Konfiguration (aus TOML, in DB für Idempotenz)
CREATE TABLE sources (
  id            UUID PRIMARY KEY,
  type          TEXT NOT NULL,           -- 'rss' | 'youtube_channel'
  identifier    TEXT NOT NULL,           -- URL oder Channel-ID
  display_name  TEXT,
  config        JSONB NOT NULL,
  enabled       BOOLEAN DEFAULT TRUE,
  last_fetched  TIMESTAMPTZ
);

-- Eingelesene Rohdaten vor LLM-Verarbeitung
CREATE TABLE items (
  id            UUID PRIMARY KEY,
  source_id     UUID REFERENCES sources(id),
  external_id   TEXT NOT NULL,           -- Video-ID oder Feed-GUID
  url           TEXT NOT NULL,
  title         TEXT,
  author        TEXT,
  published_at  TIMESTAMPTZ,
  raw_text      TEXT,                    -- Volltext oder Transkript
  metadata      JSONB,                   -- Dauer, Thumbnail, Captions-Quelle, …
  fingerprint   TEXT,                    -- Hash für Dedup
  embedding     VECTOR(1024),            -- pgvector
  fetched_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (source_id, external_id)
);

-- Eine generierte Ausgabe (pro Device einmal)
CREATE TABLE editions (
  id            UUID PRIMARY KEY,
  date          DATE NOT NULL,
  device        TEXT NOT NULL,           -- 'remarkable_ppm' | 'ipad_mini' | …
  status        TEXT NOT NULL,           -- 'rendering' | 'ready' | 'delivered' | 'failed'
  json_payload  JSONB,                   -- die strukturierte Story-Liste vom LLM
  pdf_path      TEXT,
  delivered_at  TIMESTAMPTZ,
  metrics       JSONB                    -- Kosten, Tokens, Quellen-Counts
);

-- Welche Items in welcher Edition (für Cross-Day-Dedup)
CREATE TABLE edition_items (
  edition_id    UUID REFERENCES editions(id),
  item_id       UUID REFERENCES items(id),
  cluster_id    TEXT,
  rank          INT,
  PRIMARY KEY (edition_id, item_id)
);

-- Delivery-Versuche (für Retries und Audit)
CREATE TABLE deliveries (
  id            UUID PRIMARY KEY,
  edition_id    UUID REFERENCES editions(id),
  channel       TEXT NOT NULL,           -- 'remarkable' | 'filesystem' | 'email'
  target        TEXT,                    -- E-Mail-Adresse, RM-Folder-Pfad, …
  status        TEXT NOT NULL,           -- 'pending' | 'success' | 'failed'
  error         TEXT,
  attempted_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. Konfigurationsformat

```toml
[user]
timezone       = "Europe/Berlin"
delivery_time  = "06:30"                # lokale Zeit
language       = "de"                   # Output-Sprache der Zeitung
max_stories    = 12

[llm]
# LiteLLM-Provider-Strings, austauschbar:
#   "anthropic/claude-sonnet-4-6"
#   "openai/gpt-5"
#   "ollama/qwen3:32b"
#   "groq/llama-3.3-70b-versatile"
ranker_model    = "anthropic/claude-haiku-4-5"
writer_model    = "anthropic/claude-sonnet-4-6"
embedding_model = "openai/text-embedding-3-small"
api_keys_env    = true                  # Keys aus ENV, nicht im TOML

[asr]
backend        = "faster-whisper"       # oder "groq" für Cloud-Speed
model_size     = "medium"
language       = "auto"

# ─── Delivery: mehrere Kanäle parallel möglich ──────────────────────────────
[delivery]
devices        = ["remarkable_ppm", "ipad_mini", "generic_a5"]

[delivery.remarkable]
enabled        = true
device_profile = "remarkable_ppm"       # welches Profile per rmapi pushen
folder         = "Newspaper"
keep_days      = 30                     # alte Editions in Archive, außer annotiert

[delivery.filesystem]
enabled        = true
output_dir     = "/app/output"          # User syncs selbst (Syncthing, USB)

[delivery.email]
enabled        = true
device_profile = "kindle_paperwhite"    # welches Profile per Mail schicken
to             = ["meine-mail@example.com", "meinkindle@kindle.com"]
from_name      = "Lemonade Daily"
subject_template = "Lemonade — {date:%A, %d. %B %Y}"
# SMTP-Settings aus ENV: LEMONADE_SMTP_HOST, _PORT, _USER, _PASS, _FROM
attach_pdf     = true
include_summary_in_body = true          # Plaintext-Headlines im Mail-Body

# ─── Quellen ────────────────────────────────────────────────────────────────
[[rss]]
url            = "https://www.lesswrong.com/feed.xml"
category       = "Longform"

[[rss]]
url            = "https://feeds.arstechnica.com/arstechnica/index"
category       = "Tech"
follow_links   = true                   # Volltext nachladen wenn Feed nur Teaser

[[youtube]]
channel_id     = "UCBa659QWEk1AI4tG9mmH4-A"   # Two Minute Papers
category       = "AI"
min_duration_s = 180                    # Shorts ignorieren

[[youtube]]
channel_handle = "@simonwillison"
category       = "AI"
```

---

## 6. Device-Profile

PDF wird **pro Device einmal** gerendert. Profile sind YAML-Dateien im Repo, Community-PRs willkommen.

### MVP-Set (deckt ~80% der Zielgruppe ab)

| Profile-ID | Device | Trim (mm) | Resolution (px) | Notes |
|---|---|---|---|---|
| `remarkable_ppm` | reMarkable Paper Pro Move | 107.8 × 195.6 | 954 × 1696 | Color, Gallery 3, 264 ppi |
| `remarkable_pp` | reMarkable Paper Pro 11.8" | 196 × 261 | 1620 × 2160 | Color, 229 ppi |
| `remarkable_2` | reMarkable 2 | 157 × 209 | 1404 × 1872 | Mono, Carta, 226 ppi |
| `kindle_paperwhite` | Kindle Paperwhite (12. Gen) | 91 × 122 | 1236 × 1648 | Mono, 7", 300 ppi |
| `ipad_mini` | iPad mini 8.3" | 134.8 × 195.4 | 2266 × 1488 | Color, 326 ppi |
| `generic_a5` | DIN A5 | 148 × 210 | — | Vector, geräteneutral, druckbar |

### Was ein Device-Profile definiert

```yaml
# device_profiles/remarkable_ppm.yaml
id: remarkable_ppm
display_name: "reMarkable Paper Pro Move"
page:
  width_mm: 107.8
  height_mm: 195.6
  margin_top_mm: 12
  margin_bottom_mm: 14         # extra für Daumen
  margin_inner_mm: 10
  margin_outer_mm: 10
typography:
  body_family: "Source Serif 4"
  body_size_pt: 11
  body_leading_pt: 14.5
  heading_family: "Inter"
  heading_h1_pt: 22
  heading_h2_pt: 16
color:
  enabled: true
  palette: "muted"             # 'muted' für Gallery-3, 'mono' für Carta
rendering:
  embed_bookmarks: true
  hyperlinks: short_url        # 'inline' | 'short_url' | 'footnote'
  image_max_width_pct: 100
  image_dither: floyd_steinberg
delivery:
  default_channel: "remarkable_cloud"
```

Das Typst-Template liest Profile + Edition als JSON-Inputs. **Ein Template, alle Profile.**

---

## 7. Stages im Detail

### 7.1 Ingestion

#### RSS-Adapter

```python
class RSSAdapter(SourceAdapter):
    async def fetch(self, source: Source, since: datetime) -> list[Item]:
        feed = feedparser.parse(source.identifier)
        items = []
        for entry in feed.entries:
            published = parse_date(entry.published)
            if published < since:
                continue
            text = entry.get("content", [{}])[0].get("value") or entry.summary
            if source.config.get("follow_links") and len(text) < 500:
                text = await self._fetch_fulltext(entry.link)  # trafilatura
            items.append(Item(
                external_id=entry.id or entry.link,
                url=entry.link,
                title=entry.title,
                author=entry.get("author"),
                published_at=published,
                raw_text=clean_html(text),
                metadata={"source_type": "rss"},
            ))
        return items
```

#### YouTube-Adapter (mit dreistufigem Transcript-Fallback)

```python
class YouTubeAdapter(SourceAdapter):
    async def fetch(self, source: Source, since: datetime) -> list[Item]:
        channel_id = self._resolve_channel_id(source)
        # Discovery via Channel-RSS — keine API-Key nötig
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)

        items = []
        for entry in feed.entries:
            video_id = entry.yt_videoid
            if entry.published_parsed < since:
                continue
            duration = await self._fetch_duration(video_id)
            if duration < source.config.get("min_duration_s", 0):
                continue

            transcript = await self._get_transcript(video_id)
            items.append(Item(
                external_id=video_id,
                url=f"https://youtube.com/watch?v={video_id}",
                title=entry.title,
                author=entry.author,
                published_at=parse_date(entry.published),
                raw_text=transcript.text,
                metadata={
                    "source_type": "youtube",
                    "duration_s": duration,
                    "transcript_source": transcript.source,
                    "thumbnail": entry.media_thumbnail[0]["url"],
                },
            ))
        return items

    async def _get_transcript(self, video_id: str) -> Transcript:
        # 1) Manuell erstellte Captions (höchste Qualität)
        try:
            t = YouTubeTranscriptApi().fetch(video_id, languages=['de', 'en'])
            return Transcript(text=join_segments(t),
                              source=f"native_{t.language_code}")
        except (TranscriptsDisabled, NoTranscriptFound):
            pass

        # 2) Auto-generated Captions
        try:
            t = YouTubeTranscriptApi().fetch(video_id)
            return Transcript(text=join_segments(t),
                              source=f"auto_{t.language_code}")
        except Exception:
            pass

        # 3) Whisper als Last-Resort
        return await self._whisper_transcribe(video_id)

    async def _whisper_transcribe(self, video_id: str) -> Transcript:
        audio_path = await yt_dlp_audio(video_id)        # m4a-only
        try:
            result = await whisper_pool.transcribe(audio_path, model="medium")
            return Transcript(text=result.text, source="whisper")
        finally:
            audio_path.unlink(missing_ok=True)
```

**Whisper-Hinweis:** Auf Single-CPU-vServer ist `medium` für 30-Min-Videos ~5–10 Minuten — okay für Nacht-Cron, nicht für Realtime. Ohne GPU ist [Groq Whisper](https://groq.com) (~0.04 USD/Stunde Audio) eine pragmatische Cloud-Alternative; via LiteLLM-kompatibler ENV-Variable bleibt der Provider-Switch trivial.

### 7.2 Curation & Summarization

Zwei LLM-Pässe, getrennt weil unterschiedliche Modell-Stärken gefragt sind:

**Pass 1 — Cluster + Rank** (günstiges Modell, z.B. Haiku 4.5 / GPT-5-mini / Llama-3.3):

1. Embeddings aller heutigen Items, die nicht in vorherigen Editionen waren.
2. Clustering per pgvector-KNN, Cosine-Threshold 0.85 — fasst Duplikate zusammen, wenn drei Quellen dasselbe Ereignis bringen.
3. Pro Cluster Repräsentant wählen: Originalquelle vor Aggregator, längster Text als Tie-Break.
4. LLM rankt mit strukturiertem Prompt:

```
Du bekommst N Story-Cluster. Bewerte jedes nach:
- relevance (0–10): Wichtigkeit unabhängig vom User
- novelty (0–10): wie neu ist die Information
- depth (0–10): substantieller Beitrag vs. Boulevard

Antwort als JSON-Array: [{cluster_id, relevance, novelty, depth, reason}]
```

5. Top-N (aus `max_stories`) gehen weiter.

**Pass 2 — Schreiben** (starkes Modell, Sonnet 4.6 / GPT-5 / Opus 4.7):

Pro Story strukturierter JSON-Output via Tool-Calling:

```json
{
  "headline": "...",       // ≤ 8 Wörter
  "deck": "...",           // 1 Satz Untertitel
  "body": "...",           // 80–150 Wörter, harte Begrenzung
  "category": "Tech",
  "sources": [
    {"title": "...", "url": "...", "domain": "lesswrong.com"}
  ],
  "pull_quote": "..."      // optional, max 15 Wörter
}
```

Komplette Edition als JSON:

```json
{
  "edition_date": "2026-05-09",
  "lead_story": { ... },
  "sections": [
    {"name": "Tech & AI", "stories": [...]},
    {"name": "Watched", "stories": [...]}
  ],
  "metadata": {
    "tokens_in": 28401,
    "tokens_out": 8230,
    "cost_usd": 0.18,
    "sources_count": {"rss": 14, "youtube": 6}
  }
}
```

**Warum strukturierter JSON-Output?** Style (Layout, Typografie, Sprache) und Substanz (Stories) bleiben entkoppelt. Template tauschen ohne LLM-Re-Run, LLM tauschen ohne Layout-Bruch.

**Kosten-Sanity:** 12 Stories × ~800 Output-Token = ~10k out, plus ~40k in (Transkripte sind lang). Sonnet 4.6: ~0.20 USD pro Edition, ~6 USD/Monat. Lokales Ollama Qwen3-32B: ~0 USD, ~10 Min auf einer 4090.

### 7.3 Rendering

Pro konfiguriertem Device einmal Typst aufrufen:

```bash
typst compile \
  --input "edition=$(cat edition.json)" \
  --input "profile=$(yq -o json profiles/remarkable_ppm.yaml)" \
  templates/newspaper.typ \
  output/2026-05-09_remarkable_ppm.pdf
```

Template-Skizze:

```typst
#let edition = json(sys.inputs.edition)
#let profile = json(sys.inputs.profile)

#set page(
  width:  profile.page.width_mm * 1mm,
  height: profile.page.height_mm * 1mm,
  margin: (
    top:    profile.page.margin_top_mm * 1mm,
    bottom: profile.page.margin_bottom_mm * 1mm,
    inside: profile.page.margin_inner_mm * 1mm,
    outside: profile.page.margin_outer_mm * 1mm,
  ),
)
#set text(
  font: profile.typography.body_family,
  size: profile.typography.body_size_pt * 1pt,
)

#cover(edition)
#lead-story(edition.lead_story, profile)
#for section in edition.sections {
  section-page(section, profile)
}
#colophon(edition.metadata)
```

`#outline` erzeugt Bookmarks → auf reMarkable wird das die Section-Sidebar.

### 7.4 Delivery

Drei Kanäle im MVP, parallel konfigurierbar:

#### 7.4.1 reMarkable Cloud via rmapi

```python
class RemarkableDelivery(DeliveryChannel):
    async def deliver(self, edition: Edition, pdf_path: Path):
        target = f"/{config.delivery.remarkable.folder}/{edition.date:%Y-%m}/"
        await rmapi(["mkdir", "-p", target])
        await rmapi(["put", str(pdf_path), target])
        # "Latest" für stabilen Pfad
        await rmapi(["put", str(pdf_path),
                     f"/{config.delivery.remarkable.folder}/Latest.pdf"])
```

**Cleanup-Job** (täglich, vor Generation):

1. Editionen älter als `keep_days` finden.
2. `rmapi stat` → prüfen ob Datei verändert wurde (Annotationen → Metadata-Änderung).
3. Wenn unverändert: in `Newspaper/Archive/` schieben statt löschen.
4. Annotierte Editionen werden nie automatisch entfernt — kein Datenverlust.

#### 7.4.2 Filesystem

```python
class FilesystemDelivery(DeliveryChannel):
    """Geräteneutraler Fallback. User syncs selbst (Syncthing, USB, Dropbox)."""
    async def deliver(self, edition: Edition, pdf_path: Path):
        dest = self.output_dir / f"{edition.device}_{edition.date:%Y-%m-%d}.pdf"
        shutil.copy(pdf_path, dest)
```

#### 7.4.3 E-Mail

Banal, aber universell: PDF als Attachment per SMTP. Funktioniert für Kindle-Send-to-Kindle, ältere reMarkables ohne Cloud-Abo, Mitlesen am Desktop, Familie/Team-Distribution.

```python
class EmailDelivery(DeliveryChannel):
    """SMTP-Versand mit PDF-Attachment.

    Für Kindle: 'meinkindle@kindle.com' eintragen, Send-to-Kindle versendet
    automatisch ans Gerät. Kein Push, aber zuverlässig.
    """
    def __init__(self, settings: EmailSettings):
        self.smtp = settings  # host, port, user, pass, from aus ENV

    async def deliver(self, edition: Edition, pdf_path: Path):
        msg = EmailMessage()
        msg["From"] = f"{self.smtp.from_name} <{self.smtp.from_addr}>"
        msg["To"] = ", ".join(self.smtp.to)
        msg["Subject"] = self.smtp.subject_template.format(date=edition.date)

        body = self._render_body(edition) if self.smtp.include_summary else ""
        msg.set_content(body or "Deine Lemonade-Ausgabe von heute liegt im Anhang.")

        with pdf_path.open("rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=pdf_path.name,
            )

        async with aiosmtplib.SMTP(
            hostname=self.smtp.host,
            port=self.smtp.port,
            use_tls=self.smtp.port == 465,
            start_tls=self.smtp.port == 587,
        ) as client:
            await client.login(self.smtp.user, self.smtp.password)
            await client.send_message(msg)

    def _render_body(self, edition: Edition) -> str:
        """Plaintext-Headlines fürs Mail-Preview."""
        payload = edition.json_payload
        lines = [f"Lemonade — {edition.date:%A, %d. %B %Y}", ""]
        lines.append(f"▸ {payload['lead_story']['headline']}")
        for section in payload['sections']:
            lines.append(f"\n{section['name'].upper()}")
            for story in section['stories']:
                lines.append(f"  • {story['headline']}")
        lines.append("\n— Vollausgabe im Anhang —")
        return "\n".join(lines)
```

**SMTP-Konfiguration via ENV** (nicht ins TOML, weil Secrets):

```bash
LEMONADE_SMTP_HOST=smtp.fastmail.com
LEMONADE_SMTP_PORT=587
LEMONADE_SMTP_USER=lemonade@example.com
LEMONADE_SMTP_PASS=xxxxxxxxxxxxxxxx
LEMONADE_SMTP_FROM=lemonade@example.com
```

**Kindle-Anwendungsfall:** User setzt `to = ["xyz@kindle.com"]` und whitelistet die Sender-Adresse in seinem Amazon-Konto. Das Format ist dann typischerweise `kindle_paperwhite`.

**Anti-Pattern: Tracking-Pixel oder HTML-Mails.** Im OSS-Geist: Plaintext-Body + PDF-Attachment, fertig.

### 7.5 Delivery-Orchestrierung

```python
async def deliver_edition(edition: Edition, channels: list[DeliveryChannel]):
    """Best-effort: jeder Kanal eigenständig, keiner blockt die anderen."""
    results = await asyncio.gather(
        *[c.deliver(edition, edition.pdf_path) for c in channels],
        return_exceptions=True,
    )
    for channel, result in zip(channels, results):
        record_delivery(edition, channel, result)
        if isinstance(result, Exception):
            logger.error(f"Delivery via {channel.name} failed: {result}")
```

---

## 8. Repo-Struktur

```
lemonade/
├── pyproject.toml
├── README.md
├── KONZEPT.md                     # dieses Dokument
├── docker-compose.yml
├── Dockerfile
├── .env.example
│
├── lemonade/
│   ├── __init__.py
│   ├── cli.py                     # Typer-CLI
│   ├── config.py                  # TOML-Loader, Pydantic
│   ├── db.py
│   │
│   ├── adapters/
│   │   ├── base.py                # SourceAdapter ABC
│   │   ├── rss.py
│   │   └── youtube.py
│   │
│   ├── pipeline/
│   │   ├── ingest.py
│   │   ├── cluster.py
│   │   ├── rank.py
│   │   ├── write.py
│   │   └── orchestrate.py         # Cron-Entry-Point
│   │
│   ├── llm/
│   │   ├── client.py              # LiteLLM-Wrapper
│   │   └── prompts/
│   │       ├── rank.py
│   │       └── write.py
│   │
│   ├── render/
│   │   ├── typst_runner.py
│   │   └── profiles.py
│   │
│   └── delivery/
│       ├── base.py
│       ├── remarkable.py
│       ├── filesystem.py
│       └── email.py
│
├── templates/
│   ├── newspaper.typ              # Haupt-Template
│   ├── components/
│   │   ├── cover.typ
│   │   ├── story.typ
│   │   └── colophon.typ
│   └── fonts/
│
├── device_profiles/
│   ├── remarkable_ppm.yaml
│   ├── remarkable_pp.yaml
│   ├── remarkable_2.yaml
│   ├── kindle_paperwhite.yaml
│   ├── ipad_mini.yaml
│   └── generic_a5.yaml
│
├── examples/
│   └── config.example.toml
│
└── tests/
    ├── adapters/
    ├── pipeline/
    └── fixtures/                  # gespeicherte Feeds + YT-Responses
```

---

## 9. Deployment

### Docker Compose (Single-User MVP)

```yaml
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://lemonade:${DB_PASS}@db:5432/lemonade
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LEMONADE_SMTP_HOST=${SMTP_HOST}
      - LEMONADE_SMTP_PORT=${SMTP_PORT}
      - LEMONADE_SMTP_USER=${SMTP_USER}
      - LEMONADE_SMTP_PASS=${SMTP_PASS}
      - LEMONADE_SMTP_FROM=${SMTP_FROM}
      - TZ=Europe/Berlin
    volumes:
      - ./config.toml:/app/config.toml:ro
      - ./output:/app/output
      - rmapi-config:/root/.config/rmapi
    depends_on: [db]

  db:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=lemonade
      - POSTGRES_PASSWORD=${DB_PASS}
      - POSTGRES_DB=lemonade
    volumes:
      - pgdata:/var/lib/postgresql/data

  cron:
    image: alpine:3
    command: |
      sh -c 'echo "30 4 * * * docker exec lemonade-app lemonade run" | crontab -
             && crond -f'
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

volumes:
  pgdata:
  rmapi-config:
```

### Erstmaliges Setup

```bash
git clone https://github.com/<you>/lemonade.git
cd lemonade
cp .env.example .env                               # API-Keys, SMTP eintragen
cp examples/config.example.toml config.toml
docker compose up -d db
docker compose run --rm app lemonade init          # DB-Schema
docker compose run --rm app lemonade rmapi-auth    # OTP-Pairing
docker compose run --rm app lemonade preview       # Trockenlauf
docker compose up -d                                # Cron läuft
```

**Dimensionierung:** Hetzner CX22 (2 vCPU, 4 GB, ~5 EUR/Monat) reicht für ~10 RSS + ~20 YouTube-Kanäle ohne lokales Whisper. Mit lokalem Whisper besser CX32 oder Mini-PC mit GPU.

---

## 10. CLI-Kommandos

```bash
lemonade run                          # Vollpipeline heute, alle Devices, Push
lemonade run --device remarkable_ppm --no-deliver
lemonade preview                      # PDF generieren, Browser-Preview, kein Push
lemonade backfill 2026-05-01..2026-05-07
lemonade sources test rss             # Adapter-Diagnose
lemonade sources list
lemonade devices list
lemonade edition show 2026-05-09
lemonade costs --month
lemonade rmapi-auth                   # OTP-Pairing
lemonade email-test                   # SMTP-Verbindung prüfen, Test-Mail
```

---

## 11. Roadmap

### MVP (Wochen 1–4)

- [ ] Repo-Skeleton, Pydantic-Config, DB-Schema
- [ ] RSS-Adapter + YouTube-Adapter mit dreistufigem Transcript-Fallback
- [ ] LiteLLM-Pipeline (Cluster, Rank, Write) mit JSON-Output
- [ ] Typst-Template + 3 Device-Profile (PPM, PP, A5-Generic)
- [ ] Delivery-Channels: rmapi, Filesystem, E-Mail
- [ ] Docker Compose, README mit Quickstart
- [ ] Eigener Daily-Run grünt eine Woche durch

### v1.1 (Polish & Reichweite)

- [ ] Kindle-, iPad-mini-, RM2-Profile produktionsreif
- [ ] Annotation-aware Cleanup (rmapi stat-basiert)
- [ ] Prefect statt Cron (Retries, UI-Logs)
- [ ] OPML-Import für RSS
- [ ] Image-Embedding (Thumbnails als gedithered Bilder)
- [ ] HTML-Mail-Variante als Option (für Newsletter-Use-Cases)

### v1.2 (Community)

- [ ] Plugin-System für Source-Adapter (X als ersten externen)
- [ ] Template-Gallery / Theme-Switcher
- [ ] One-Click-Deploy auf Railway/Fly.io
- [ ] Dokumentations-Site mit MkDocs

### v2.0 (Reasoning-Layer)

Hier wird die NotebookLM-Frage relevant. Zwei Wege, schließen sich nicht aus:

- **(a) Open Notebook integrieren.** [Open Notebook](https://github.com/lfnovo/open-notebook) ist ein OSS-NotebookLM-Klon mit Source-Library. Lemonades Item-Korpus als Open-Notebook-Sources spiegeln; User bekommt zusätzlich zur PDF ein Web-UI für Q&A.
- **(b) Eigene Long-Term-Memory in pgvector.** Der RAG-Layer (LangChain oder llama-index) erlaubt Fragen wie „Was hat Karpathy diese Woche zu RL gesagt?" — und beim Ranking kann das LLM auf Historie zugreifen („dieses Thema hatten wir vorgestern bereits prominent").

Vorschlag: **(b) als interne Capability der Pipeline (Cross-Edition-Awareness), (a) als optionales Companion-Tool für Power-User.** Beides nicht für MVP.

---

## 12. Bewusste Trade-offs

- **Kein Web-UI im MVP.** TOML editieren ist für die Zielgruppe zumutbar und spart 4 Wochen Frontend.
- **Postgres statt SQLite.** Overkill für Single-User, aber pgvector ist's wert; der Schritt zu Multi-User wird trivial.
- **Typst statt LaTeX/HTML.** Niedrigere Einstiegshürde für Community-Templates.
- **Cron statt Scheduler.** Niemand will eine zweite Sache lernen, bevor das Hauptding läuft.
- **rmapi als Subprozess statt Library.** Weil rmapi-js und rmapy weniger aktiv sind als der ddvk-Go-Fork.
- **Whisper `medium` als Default.** `large-v3` ist genauer aber 3× langsamer; für Newspaper-Zwecke unnötig.
- **E-Mail als Plaintext + PDF, kein HTML.** OSS-Geist, keine Tracker, kompatibel mit Send-to-Kindle.

---

## 13. Risiken & Mitigations

| Risiko | Wahrsch. | Impact | Mitigation |
|---|---|---|---|
| reMarkable-Cloud-Sync-Protokoll ändert sich | Mittel | Hoch | Adapter-Pattern, ddvk-Fork als Fallback, Filesystem-Delivery als Always-Works-Backup |
| YouTube blockiert Transcript-API per IP | Mittel | Mittel | yt-dlp-Fallback, optional Residential-Proxies (Webshare-Integration vorbereiten) |
| LLM-Provider-Outage | Niedrig | Niedrig | LiteLLM-Fallback-Liste, lokales Ollama als Last-Resort |
| Whisper braucht zu lange ohne GPU | Hoch (CPU-only) | Mittel | Groq-Whisper als Cloud-Alternative, oder `min_duration_s` höher |
| LLM-Output sprengt Layout (zu viel Text) | Hoch | Niedrig | Validation: bei >150 Wörter Body abschneiden, einmal Re-Prompt, dann hart truncaten |
| YouTube-Captions in falscher Sprache | Mittel | Niedrig | Translate-Step im Adapter (LiteLLM oder Whisper-translate) |
| SMTP wird vom Provider als Spam markiert | Mittel | Niedrig | SPF/DKIM-Setup dokumentieren, Plaintext-Body, kein Tracking |

---

## 14. Was als Nächstes passiert (Claude Code Handover)

Mit Claude Code in dieser Reihenfolge bauen:

1. **Repo-Init** — `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, leere Modul-Struktur per §8.
2. **DB-Layer** — Alembic-Migrationen für Schema aus §4, SQLAlchemy-Models.
3. **Config-Layer** — Pydantic-Models, TOML-Loader, ENV-Override für Secrets.
4. **RSS-Adapter** — minimaler Working-Prototype mit `feedparser` + `trafilatura`.
5. **YouTube-Adapter** — Channel-RSS + youtube-transcript-api + yt-dlp-Audio + faster-whisper.
6. **LLM-Stage** — LiteLLM-Wrapper, Cluster-Schritt mit pgvector, Rank- und Write-Prompts.
7. **Render-Stage** — Typst-Runner, erstes Template für `remarkable_ppm`.
8. **Delivery-Channels** — rmapi-Wrapper, Filesystem, E-Mail.
9. **CLI + Orchestrierung** — Typer-Commands, Pipeline-Entry-Point.
10. **End-to-End-Test** — eine Woche eigener Daily-Run.

**Geschätzter Aufwand bis lauffähiger Spike:** ~1 Tag fokussierte Arbeit für Schritte 1+4+6+7+9 (RSS-only, ein Device, ein Channel). Volle MVP-Funktionalität: ~3–4 Wochen.

---

*Lemonade — When life gives you 800 RSS items, make Lemonade.*
