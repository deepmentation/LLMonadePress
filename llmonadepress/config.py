from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from llmonadepress.llm.prompts.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


class UserConfig(BaseModel):
    timezone: str = "Europe/Berlin"
    delivery_time: str = "06:30"
    language: str = DEFAULT_LANGUAGE
    max_stories: int = 12

    @field_validator("language")
    @classmethod
    def _validate_language(cls, v: str) -> str:
        v = v.lower()
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language {v!r}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        return v


class LLMConfig(BaseModel):
    ranker_model: str = "anthropic/claude-haiku-4-5"
    writer_model: str = "anthropic/claude-sonnet-4-6"
    embedding_model: str = "openai/text-embedding-3-small"
    api_keys_env: bool = True


class ASRConfig(BaseModel):
    # backend ∈ {"faster-whisper", "litellm", "off"}
    #   "faster-whisper": local CPU/GPU via faster-whisper (model_size applies)
    #   "litellm":        any LiteLLM transcription model (model field used)
    #                     e.g. "openrouter/openai/whisper-large-v3-turbo"
    #                     or "openai/whisper-1", "groq/whisper-large-v3"
    #   "off":            skip Tier 3 — videos without captions are dropped
    backend: str = "off"
    model: str = "openrouter/openai/whisper-large-v3-turbo"
    model_size: str = "medium"
    language: str = "auto"


class RemarkableDeliveryConfig(BaseModel):
    enabled: bool = False
    device_profile: str = "remarkable_ppm"
    folder: str = "Newspaper"
    keep_days: int = 30


class FilesystemDeliveryConfig(BaseModel):
    enabled: bool = True
    output_dir: str = "/app/output"


class EmailDeliveryConfig(BaseModel):
    enabled: bool = False
    device_profile: str = "kindle_paperwhite"
    to: list[str] = Field(default_factory=list)
    from_name: str = "LLMonadePress Daily"
    subject_template: str = "LLMonadePress — {date:%A, %d. %B %Y}"
    attach_pdf: bool = True
    include_summary_in_body: bool = True


class DeliveryConfig(BaseModel):
    devices: list[str] = Field(default_factory=lambda: ["generic_a5"])
    remarkable: RemarkableDeliveryConfig = Field(default_factory=RemarkableDeliveryConfig)
    filesystem: FilesystemDeliveryConfig = Field(default_factory=FilesystemDeliveryConfig)
    email: EmailDeliveryConfig = Field(default_factory=EmailDeliveryConfig)


class RSSSource(BaseModel):
    url: str
    category: str = "General"
    follow_links: bool = False


class YouTubeSource(BaseModel):
    channel_id: str | None = None
    channel_handle: str | None = None
    category: str = "General"
    min_duration_s: int = 0


class SMTPSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEMONADE_SMTP_",
        populate_by_name=True,
    )

    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    from_addr: str = Field(default="", validation_alias="LEMONADE_SMTP_FROM")


class LLMonadePressConfig(BaseModel):
    user: UserConfig = Field(default_factory=UserConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    asr: ASRConfig = Field(default_factory=ASRConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    rss: list[RSSSource] = Field(default_factory=list)
    youtube: list[YouTubeSource] = Field(default_factory=list)


def load_config(path: Path = Path("config.toml")) -> LLMonadePressConfig:
    path = Path(path)
    if path.is_dir():
        raise IsADirectoryError(
            f"{path} exists as a directory, not a file. "
            "This usually happens when Docker's bind mount auto-creates a "
            "missing source path. Remove the directory and create the file: "
            f"`rmdir {path} && cp examples/config.example.toml {path}`"
        )
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. "
            "Copy examples/config.example.toml to config.toml and edit it."
        )
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return LLMonadePressConfig.model_validate(data)
