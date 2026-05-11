# AI Coding Guide — LLMonadePress

This document helps AI coding assistants understand and contribute to LLMonadePress effectively.

## Architecture Rules

1. **Five decoupled stages.** Ingestion → Curation → Rendering → Delivery. Each stage communicates via DB + filesystem, never in-memory. Each stage must be independently re-runnable.

2. **Structured JSON between LLM and Renderer.** The LLM outputs structured JSON (stories with headline, deck, body, sources). Typst reads this JSON. Never embed layout logic in LLM prompts.

3. **Provider neutrality.** All LLM calls go through LiteLLM. Never import provider SDKs directly. Config determines the model, not code.

4. **Device profiles are data, not code.** Adding a new device = adding a YAML file. No code changes needed.

5. **Secrets in ENV, config in TOML.** API keys, SMTP passwords → environment variables. Sources, preferences → config.toml.

## Code Style

- Python 3.12 with full type annotations
- Async by default (asyncpg, aiosmtplib, httpx)
- SQLAlchemy 2.0 style: `Mapped`, `mapped_column`, async sessions
- Pydantic v2 for all config/validation models
- Ruff for linting and formatting (line-length 99)
- No comments unless explaining WHY (not what)
- No docstrings on private methods

## Testing

- Use pytest with pytest-asyncio (auto mode)
- Test fixtures go in `tests/fixtures/`
- Mock external services (LLM, YouTube API, SMTP) — never call real APIs in tests
- Use `respx` for HTTP mocking, `unittest.mock` for subprocess mocking
- Integration tests with testcontainers for Postgres when needed
- TDD: write the failing test first, then implement

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix  
- `docs:` — documentation only
- `chore:` — build, CI, tooling
- `refactor:` — code change that neither fixes nor adds
- `test:` — adding or correcting tests

## Common Patterns

### Adding a new source adapter

1. Create `llmonadepress/adapters/newadapter.py` implementing `SourceAdapter` ABC
2. Add tests in `tests/adapters/test_newadapter.py`
3. Register in adapter dispatch (`llmonadepress/pipeline/ingest.py`)
4. Add config section to Pydantic models in `llmonadepress/config.py`

### Adding a new device profile

1. Create `device_profiles/new_device.yaml` following existing profile schema
2. No code changes needed — Typst template reads profile dynamically
3. Add a small test in `tests/render/test_profiles.py` that loads the new YAML

### Adding a new delivery channel

1. Create `llmonadepress/delivery/newchannel.py` implementing `DeliveryChannel` ABC
2. Add tests in `tests/delivery/test_newchannel.py`
3. Register in delivery orchestration (`llmonadepress/pipeline/orchestrate.py`)
4. Add a config block to `[delivery]` Pydantic models in `llmonadepress/config.py`

### Adding a new output language

1. Add a `PromptPack` entry to `llmonadepress/llm/prompts/i18n.py`
2. Add the language code to `[tool.llmonadepress] supported_languages` in
   `pyproject.toml`. The `test_pyproject_declares_supported_languages`
   regression test enforces sync between the two.

## LLM Prompt Guidelines

- Prompts live in `llmonadepress/llm/prompts/` as Python modules with
  per-language packs in `i18n.py`
- Always request structured JSON output
- Include output schema in the prompt
- Set hard word limits (e.g., body: 80-150 words)
- Validate the parsed result against shape (see `llmonadepress/pipeline/write.py`)
- Test prompt construction (not LLM output) in unit tests
- LLM responses are noisy: rely on `_extract_json` (`llmonadepress/llm/client.py`)
  which already handles fences, smart-quote breakage, list-wrapping, etc.
