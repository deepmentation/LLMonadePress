# Contributing to LLMonadePress

Thanks for taking the time! LLMonadePress is in active early development —
the architecture is settled but plenty of polish and reach is open. This
guide covers how to get a working dev setup, what conventions to follow,
and where the lowest-friction first contributions live.

---

## Getting set up

Prerequisites: Python 3.12, Docker (for the integration path), `git`.

```bash
git clone https://github.com/deepmentation/LLMonadePress.git
cd LLMonadePress
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                       # 76+ tests should pass
```

For an end-to-end run (needs Docker):

```bash
cp .env.example .env                         # add at least one *_API_KEY
cp examples/config.example.toml config.toml  # add a feed or YouTube channel
docker compose up -d db
docker compose run --rm app init
docker compose run --rm app preview          # writes a PDF into ./output/
```

---

## Where things live

```
llmonadepress/        # the package; CLI command stays `lemonade`
  adapters/           # source adapters (RSS, YouTube)
  pipeline/           # ingest, cluster, rank, write, orchestrate
  llm/                # LiteLLM wrapper + prompt templates (i18n: en/de/fr)
  render/             # Typst runner + device profile loader
  delivery/           # filesystem, email, reMarkable
device_profiles/      # YAML per device — community PRs welcome
templates/            # Typst templates (one for all devices)
examples/             # config.example.toml
tests/                # pytest, mirrors the package layout
KONZEPT.md            # the spec (German)
GAP.md                # living roadmap: spec vs. current code
CLAUDE.md             # project overview for AI assistants
AI-CODING-GUIDE.md    # rules for AI-assisted contributions
```

---

## Workflow

1. **Open an issue first** for anything bigger than a typo, so we can agree
   on the approach before you spend time on it.
2. **Branch from `main`**: `git checkout -b feat/your-thing` (use `feat/`,
   `fix/`, `docs/`, `chore/` prefixes — see commit conventions below).
3. **Make focused commits**. One logical change per commit.
4. **Run the test suite** locally: `pytest`. Add tests for the change.
5. **Run lint**: `ruff check . && ruff format --check .`.
6. **Open a pull request** against `main`. The PR description should explain
   *why*, not just *what* — the code shows what.

### Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org):

- `feat:` — user-visible new functionality
- `fix:` — bug fix
- `docs:` — documentation only
- `chore:` — tooling, build, CI
- `refactor:` — code change that neither fixes nor adds
- `test:` — adding or correcting tests

Keep the subject under 72 chars. Use the body for the *why*.

---

## Code style

- **Python 3.12**, full type annotations, async by default.
- **SQLAlchemy 2.0** style: `Mapped`, `mapped_column`, async sessions.
- **Pydantic v2** for all config / validation models.
- **Ruff** is the linter and formatter (line length 99). `ruff format .`.
- **No comments unless explaining the *why***. Don't restate what the code
  does — name things well instead.

### Architecture rules

These are non-negotiable; if a change requires breaking one, raise it in
the issue first.

1. **Five decoupled stages.** Ingest → Cluster → Rank → Write → Render →
   Deliver. Communication via DB + filesystem, never in-memory shortcuts.
   Each stage independently re-runnable.
2. **Structured JSON between LLM and renderer.** The LLM produces
   `{headline, deck, body, sources, …}`; Typst reads that JSON. Layout
   logic lives in templates, not prompts.
3. **Provider neutrality.** All LLM calls go through LiteLLM. Don't import
   provider SDKs directly. The model is config, not code. (One narrow
   exception today: `_transcribe_openrouter` does a direct REST call
   because OpenRouter's audio API isn't OpenAI-compatible.)
4. **Device profiles are data, not code.** Adding a new device = adding a
   YAML file + a test. No code change required.
5. **Secrets in ENV, content in TOML.** API keys / SMTP passwords →
   environment variables. Sources / preferences → `config.toml`. Don't
   ever commit your `config.toml` or `.env` (both are gitignored).

---

## Testing

- `pytest` — fast unit tests, fully mocked external calls.
- Use `pytest-asyncio` (auto mode is on).
- Mock external services (LLM providers, YouTube, SMTP). Never call real
  APIs from a test — `respx` for HTTP, `unittest.mock` for subprocess.
- Tests mirror the package layout: `llmonadepress/foo/bar.py` →
  `tests/foo/test_bar.py`.
- A regression test for every reported bug. We have a
  `test_extract_json_*` family that exists exactly because LLM output
  parsing surprised us — please follow that pattern.

---

## Good first contributions

Small, self-contained, and high-value:

- **A new device profile** — copy an existing YAML, measure your device
  (page mm, margins), pick fonts that exist in `fonts-dejavu-core` /
  `fonts-noto-core` (both bundled). Add a test that loads it.
- **A translation** — add a `PromptPack` entry to
  `llmonadepress/llm/prompts/i18n.py` and the language code to
  `[tool.llmonadepress] supported_languages` in `pyproject.toml`. The
  regression test `test_pyproject_declares_supported_languages` keeps
  the registry honest.
- **Better Typst rendering** — the templates in `templates/` are
  intentionally austere. Improvements to lead-story layout, pull-quote
  styling, or section dividers are very welcome.
- **A new RSS source quirk** — if you find a feed that breaks ingestion,
  open an issue with the URL and we'll add a fixture.

Bigger items are listed in [GAP.md](GAP.md) under **Aktuelle Prioritäten**.

---

## Code of conduct

Be kind, assume good intent, focus on the work. Disagreements on
direction are healthy; personal attacks aren't tolerated.

---

## Releasing (maintainers)

1. Bump `version` in `pyproject.toml` and `llmonadepress/__init__.py`.
2. Add a `## [vX.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md`.
3. Update `GAP.md` if a tracked status changed.
4. Commit with a `feat:` or `fix:` message describing the release.
5. `git tag -a vX.Y.Z -m "..."` then push tag.

Semver: `0.x.y` for now — minor bump on user-visible features, patch on
fixes. We'll switch to a proper `1.0.0` once the GAP.md priorities are
substantially closed.
