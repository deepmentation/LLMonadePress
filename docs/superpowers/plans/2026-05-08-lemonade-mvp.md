# Lemonade MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted, AI-powered daily newspaper generator that transforms RSS feeds and YouTube channels into device-optimized PDFs for E-Ink tablets.

**Architecture:** Five decoupled pipeline stages (Ingestion → Curation → Rendering → Delivery), orchestrated by CLI/Cron, communicating via Postgres + filesystem. LLM-provider-neutral via LiteLLM, device-neutral via Typst templates + YAML profiles.

**Tech Stack:** Python 3.12, Typer (CLI), PostgreSQL 16 + pgvector, SQLAlchemy + Alembic, LiteLLM, Typst, feedparser, trafilatura, youtube-transcript-api, yt-dlp, faster-whisper, aiosmtplib, Docker Compose.

---

## Phase 0: Project Foundation (Tasks 1–4)

### Task 1: Repository Skeleton & Project Config

**Files:**
- Create: `pyproject.toml`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`
- Create: `LICENSE`
- Create: `lemonade/__init__.py`
- Create: `lemonade/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`** with project metadata, dependencies, dev-dependencies, ruff/pytest config. Use `[project.scripts]` for `lemonade` CLI entry point.

- [ ] **Step 2: Create `.gitignore`** for Python, Docker, IDE files, `.env`, output PDFs.

- [ ] **Step 3: Create `LICENSE`** — MIT license.

- [ ] **Step 4: Create `.env.example`** with all ENV vars documented (DB, LLM keys, SMTP).

- [ ] **Step 5: Create `Dockerfile`** — multi-stage build, Python 3.12-slim, install Typst binary, copy project.

- [ ] **Step 6: Create `docker-compose.yml`** — app, db (pgvector/pgvector:pg16), cron services.

- [ ] **Step 7: Create GitHub templates** — bug report, feature request, PR template.

- [ ] **Step 8: Create empty module files** — `lemonade/__init__.py` (with `__version__`), `lemonade/py.typed`, `tests/__init__.py`, `tests/conftest.py`.

- [ ] **Step 9: Init git repo and commit**

```bash
git init && git add -A && git commit -m "chore: initial repo skeleton"
```

### Task 2: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create `CLAUDE.md`** with project overview, tech stack, architecture summary, coding conventions, test/lint/build commands, and key design decisions from KONZEPT.md.

### Task 3: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`** with project description, features, quickstart, configuration reference, device support table, architecture diagram, contributing guide link, license.

### Task 4: CHANGELOG.md & AI-CODING-GUIDE.md

**Files:**
- Create: `CHANGELOG.md`
- Create: `AI-CODING-GUIDE.md`

- [ ] **Step 1: Create `CHANGELOG.md`** — Keep a Changelog format, initial `[Unreleased]` section.

- [ ] **Step 2: Create `AI-CODING-GUIDE.md`** — Guidelines for AI agents working on this codebase: architecture rules, testing requirements, commit conventions, code style, LLM prompt patterns.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "docs: add CLAUDE.md, README.md, CHANGELOG.md, AI-CODING-GUIDE.md"
```

---

## Phase 1: Data Layer (Tasks 5–7)

### Task 5: Pydantic Config Models

**Files:**
- Create: `lemonade/config.py`
- Create: `examples/config.example.toml`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write tests** for TOML loading, validation, defaults, ENV override for secrets.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** Pydantic models matching KONZEPT.md §5 config format. TOML loader with `tomllib`.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Create `examples/config.example.toml`** with documented example config.
- [ ] **Step 6: Commit**

### Task 6: SQLAlchemy Models & Database Layer

**Files:**
- Create: `lemonade/db.py`
- Create: `lemonade/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write tests** for model creation, relationships, constraints.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** SQLAlchemy models for `sources`, `items`, `editions`, `edition_items`, `deliveries` per KONZEPT.md §4. Use `mapped_column`, `Mapped` type hints. pgvector `Vector(1024)` for embeddings.
- [ ] **Step 4: Implement `db.py`** — async engine factory, session factory, `init_db()`.
- [ ] **Step 5: Run tests — expect PASS**
- [ ] **Step 6: Commit**

### Task 7: Alembic Migrations

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/001_initial_schema.py`

- [ ] **Step 1: Init Alembic**, configure for async SQLAlchemy + pgvector.
- [ ] **Step 2: Generate initial migration** from models.
- [ ] **Step 3: Test migration** up and down.
- [ ] **Step 4: Commit**

---

## Phase 2: Ingestion (Tasks 8–10)

### Task 8: Source Adapter Base

**Files:**
- Create: `lemonade/adapters/__init__.py`
- Create: `lemonade/adapters/base.py`

- [ ] **Step 1: Define** `SourceAdapter` ABC with `async def fetch(source, since) -> list[Item]`.
- [ ] **Step 2: Commit**

### Task 9: RSS Adapter

**Files:**
- Create: `lemonade/adapters/rss.py`
- Create: `tests/adapters/__init__.py`
- Create: `tests/adapters/test_rss.py`
- Create: `tests/fixtures/sample_feed.xml`

- [ ] **Step 1: Create test fixture** — sample RSS/Atom XML.
- [ ] **Step 2: Write tests** — parsing, date filtering, follow_links fallback, dedup.
- [ ] **Step 3: Run tests — expect FAIL**
- [ ] **Step 4: Implement** `RSSAdapter` with feedparser + trafilatura fulltext fallback.
- [ ] **Step 5: Run tests — expect PASS**
- [ ] **Step 6: Commit**

### Task 10: YouTube Adapter

**Files:**
- Create: `lemonade/adapters/youtube.py`
- Create: `tests/adapters/test_youtube.py`
- Create: `tests/fixtures/sample_yt_feed.xml`

- [ ] **Step 1: Create test fixtures** — sample YouTube RSS XML, mock transcript responses.
- [ ] **Step 2: Write tests** — channel RSS parsing, 3-tier transcript fallback, duration filter.
- [ ] **Step 3: Run tests — expect FAIL**
- [ ] **Step 4: Implement** `YouTubeAdapter` with channel RSS, youtube-transcript-api, yt-dlp audio, faster-whisper fallback.
- [ ] **Step 5: Run tests — expect PASS**
- [ ] **Step 6: Commit**

---

## Phase 3: Curation & Summarization (Tasks 11–14)

### Task 11: LLM Client Wrapper

**Files:**
- Create: `lemonade/llm/__init__.py`
- Create: `lemonade/llm/client.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_client.py`

- [ ] **Step 1: Write tests** — LiteLLM wrapper, model selection from config, structured output.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** LiteLLM wrapper with retry, cost tracking, structured JSON output.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 12: Embedding & Clustering

**Files:**
- Create: `lemonade/pipeline/__init__.py`
- Create: `lemonade/pipeline/cluster.py`
- Create: `tests/pipeline/__init__.py`
- Create: `tests/pipeline/test_cluster.py`

- [ ] **Step 1: Write tests** — embedding generation, cosine clustering, dedup, representative selection.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** pgvector KNN clustering with cosine threshold 0.85.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 13: Ranking (LLM Pass 1)

**Files:**
- Create: `lemonade/pipeline/rank.py`
- Create: `lemonade/llm/prompts/__init__.py`
- Create: `lemonade/llm/prompts/rank.py`
- Create: `tests/pipeline/test_rank.py`

- [ ] **Step 1: Write tests** — ranking prompt construction, JSON response parsing, top-N selection.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** ranker with structured prompt (relevance/novelty/depth scoring).
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 14: Writing (LLM Pass 2)

**Files:**
- Create: `lemonade/pipeline/write.py`
- Create: `lemonade/llm/prompts/write.py`
- Create: `tests/pipeline/test_write.py`

- [ ] **Step 1: Write tests** — story generation, JSON schema validation, word count limits, edition assembly.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** writer producing structured JSON (headline, deck, body, sources, sections).
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

---

## Phase 4: Rendering (Tasks 15–17)

### Task 15: Device Profiles

**Files:**
- Create: `lemonade/render/__init__.py`
- Create: `lemonade/render/profiles.py`
- Create: `device_profiles/remarkable_ppm.yaml`
- Create: `device_profiles/remarkable_pp.yaml`
- Create: `device_profiles/remarkable_2.yaml`
- Create: `device_profiles/kindle_paperwhite.yaml`
- Create: `device_profiles/ipad_mini.yaml`
- Create: `device_profiles/generic_a5.yaml`
- Create: `tests/render/__init__.py`
- Create: `tests/render/test_profiles.py`

- [ ] **Step 1: Write tests** — YAML loading, validation, all 6 profiles parse correctly.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Create all 6 YAML profiles** per KONZEPT.md §6.
- [ ] **Step 4: Implement** `profiles.py` — Pydantic models, loader.
- [ ] **Step 5: Run tests — expect PASS**
- [ ] **Step 6: Commit**

### Task 16: Typst Template

**Files:**
- Create: `templates/newspaper.typ`
- Create: `templates/components/cover.typ`
- Create: `templates/components/story.typ`
- Create: `templates/components/colophon.typ`

- [ ] **Step 1: Create `newspaper.typ`** — main template reading edition JSON + profile JSON.
- [ ] **Step 2: Create `cover.typ`** — title page with date, edition info, lead headline.
- [ ] **Step 3: Create `story.typ`** — story layout (headline, deck, body, sources, pull quote).
- [ ] **Step 4: Create `colophon.typ`** — metadata page (sources count, costs, generation info).
- [ ] **Step 5: Commit**

### Task 17: Typst Runner

**Files:**
- Create: `lemonade/render/typst_runner.py`
- Create: `tests/render/test_typst_runner.py`
- Create: `tests/fixtures/sample_edition.json`

- [ ] **Step 1: Create test fixture** — minimal valid edition JSON.
- [ ] **Step 2: Write tests** — PDF generation, profile application, output path.
- [ ] **Step 3: Run tests — expect FAIL**
- [ ] **Step 4: Implement** `typst_runner.py` — subprocess call to `typst compile` with JSON inputs.
- [ ] **Step 5: Run tests — expect PASS**
- [ ] **Step 6: Commit**

---

## Phase 5: Delivery (Tasks 18–21)

### Task 18: Delivery Base & Filesystem

**Files:**
- Create: `lemonade/delivery/__init__.py`
- Create: `lemonade/delivery/base.py`
- Create: `lemonade/delivery/filesystem.py`
- Create: `tests/delivery/__init__.py`
- Create: `tests/delivery/test_filesystem.py`

- [ ] **Step 1: Write tests** — file copy, naming convention, directory creation.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** `DeliveryChannel` ABC + `FilesystemDelivery`.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 19: Email Delivery

**Files:**
- Create: `lemonade/delivery/email.py`
- Create: `tests/delivery/test_email.py`

- [ ] **Step 1: Write tests** — message construction, attachment, plaintext body, SMTP mock.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** `EmailDelivery` with aiosmtplib per KONZEPT.md §7.4.3.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 20: reMarkable Delivery

**Files:**
- Create: `lemonade/delivery/remarkable.py`
- Create: `tests/delivery/test_remarkable.py`

- [ ] **Step 1: Write tests** — rmapi subprocess calls, folder creation, cleanup logic.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** `RemarkableDelivery` with rmapi subprocess wrapper.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 21: Delivery Orchestration

**Files:**
- Create: `lemonade/pipeline/orchestrate.py`
- Create: `tests/pipeline/test_orchestrate.py`

- [ ] **Step 1: Write tests** — parallel delivery, partial failure handling, delivery recording.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** `deliver_edition()` with asyncio.gather, best-effort per channel.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

---

## Phase 6: CLI & Integration (Tasks 22–24)

### Task 22: Ingestion Pipeline

**Files:**
- Create: `lemonade/pipeline/ingest.py`
- Create: `tests/pipeline/test_ingest.py`

- [ ] **Step 1: Write tests** — adapter dispatch, DB persistence, dedup, embedding generation.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** `ingest()` — load sources from config, dispatch to adapters, store items.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 23: CLI Commands

**Files:**
- Create: `lemonade/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write tests** — `run`, `preview`, `sources list`, `devices list`, `email-test` commands.
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Implement** Typer CLI with all commands from KONZEPT.md §10.
- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

### Task 24: End-to-End Pipeline

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Write E2E test** — config → ingest → curate → render → filesystem delivery.
- [ ] **Step 2: Run test — expect FAIL**
- [ ] **Step 3: Wire up full pipeline** in `orchestrate.py` — `lemonade run` entry point.
- [ ] **Step 4: Run test — expect PASS**
- [ ] **Step 5: Final commit**

```bash
git add -A && git commit -m "feat: complete MVP pipeline end-to-end"
```

---

## Dependency Graph

```
Task 1 (skeleton) ──┬── Task 2 (CLAUDE.md)
                    ├── Task 3 (README.md)
                    ├── Task 4 (CHANGELOG, AI-GUIDE)
                    └── Task 5 (config) ──┬── Task 6 (models) ── Task 7 (alembic)
                                          └── Task 8 (adapter base) ──┬── Task 9 (RSS)
                                                                      └── Task 10 (YouTube)
                    Task 11 (LLM client) ──┬── Task 12 (cluster)
                                           ├── Task 13 (rank)
                                           └── Task 14 (write)
                    Task 15 (profiles) ── Task 16 (typst template) ── Task 17 (typst runner)
                    Task 18 (fs delivery) ──┬── Task 19 (email)
                                            ├── Task 20 (remarkable)
                                            └── Task 21 (orchestration)
                    Task 22 (ingest pipeline) ── Task 23 (CLI) ── Task 24 (E2E)
```

**Parallelizable groups:**
- Tasks 2, 3, 4 (docs — no code deps)
- Tasks 9, 10 (adapters — independent)
- Tasks 12, 13, 14 (pipeline stages — can develop in parallel)
- Tasks 15, 18 (render profiles + delivery base — independent)
- Tasks 19, 20 (email + remarkable — independent)
