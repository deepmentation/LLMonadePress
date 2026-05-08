from __future__ import annotations

import pytest
from pathlib import Path

from lemonade.config import (
    LemonadeConfig,
    RSSSource,
    YouTubeSource,
    SMTPSettings,
    load_config,
)


MINIMAL_TOML = b"""\
[user]
timezone = "America/New_York"

[[rss]]
url = "https://example.com/feed.xml"
category = "Tech"

[[youtube]]
channel_id = "UC123"
category = "Science"
min_duration_s = 120
"""

FULL_TOML = b"""\
[user]
timezone = "Europe/Berlin"
delivery_time = "07:00"
language = "en"
max_stories = 8

[llm]
ranker_model = "ollama/qwen3:32b"
writer_model = "openai/gpt-5"
embedding_model = "openai/text-embedding-3-small"
api_keys_env = true

[asr]
backend = "groq"
model_size = "large-v3"
language = "de"

[delivery]
devices = ["remarkable_ppm"]

[delivery.remarkable]
enabled = true
folder = "News"
keep_days = 14

[delivery.email]
enabled = true
to = ["a@b.com", "c@d.com"]

[[rss]]
url = "https://example.com/feed.xml"
category = "Tech"
follow_links = true

[[rss]]
url = "https://other.com/rss"

[[youtube]]
channel_handle = "@someone"
category = "AI"
"""


def _write_toml(tmp_path: Path, content: bytes) -> Path:
    p = tmp_path / "config.toml"
    p.write_bytes(content)
    return p


class TestLoadConfig:
    def test_load_minimal(self, tmp_path: Path) -> None:
        cfg = load_config(_write_toml(tmp_path, MINIMAL_TOML))
        assert cfg.user.timezone == "America/New_York"
        assert cfg.user.delivery_time == "06:30"  # default
        assert len(cfg.rss) == 1
        assert cfg.rss[0].url == "https://example.com/feed.xml"
        assert len(cfg.youtube) == 1
        assert cfg.youtube[0].channel_id == "UC123"

    def test_load_full(self, tmp_path: Path) -> None:
        cfg = load_config(_write_toml(tmp_path, FULL_TOML))
        assert cfg.user.max_stories == 8
        assert cfg.llm.ranker_model == "ollama/qwen3:32b"
        assert cfg.asr.backend == "groq"
        assert cfg.delivery.remarkable.enabled is True
        assert cfg.delivery.remarkable.keep_days == 14
        assert cfg.delivery.email.to == ["a@b.com", "c@d.com"]
        assert len(cfg.rss) == 2
        assert cfg.rss[1].category == "General"  # default

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/config.toml"))


class TestDefaults:
    def test_empty_toml(self, tmp_path: Path) -> None:
        cfg = load_config(_write_toml(tmp_path, b""))
        assert cfg.user.timezone == "Europe/Berlin"
        assert cfg.user.language == "de"
        assert cfg.llm.writer_model == "anthropic/claude-sonnet-4-6"
        assert cfg.asr.backend == "faster-whisper"
        assert cfg.delivery.devices == ["generic_a5"]
        assert cfg.delivery.filesystem.enabled is True
        assert cfg.delivery.email.enabled is False
        assert cfg.rss == []
        assert cfg.youtube == []


class TestRSSSources:
    def test_requires_url(self) -> None:
        with pytest.raises(Exception):
            RSSSource.model_validate({"category": "Tech"})

    def test_defaults(self) -> None:
        src = RSSSource(url="https://x.com/feed")
        assert src.category == "General"
        assert src.follow_links is False


class TestYouTubeSources:
    def test_all_optional_ids(self) -> None:
        src = YouTubeSource()
        assert src.channel_id is None
        assert src.channel_handle is None

    def test_with_handle(self) -> None:
        src = YouTubeSource(channel_handle="@test", min_duration_s=60)
        assert src.channel_handle == "@test"
        assert src.min_duration_s == 60


class TestSMTPSettings:
    def test_defaults(self) -> None:
        s = SMTPSettings()
        assert s.host == ""
        assert s.port == 587
        assert s.from_addr == ""

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LEMONADE_SMTP_HOST", "mail.example.com")
        monkeypatch.setenv("LEMONADE_SMTP_PORT", "465")
        monkeypatch.setenv("LEMONADE_SMTP_FROM", "noreply@example.com")
        s = SMTPSettings()
        assert s.host == "mail.example.com"
        assert s.port == 465
        assert s.from_addr == "noreply@example.com"
