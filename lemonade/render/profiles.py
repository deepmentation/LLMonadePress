from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from lemonade._paths import profiles_dir


class PageConfig(BaseModel):
    width_mm: float
    height_mm: float
    margin_top_mm: float = 12
    margin_bottom_mm: float = 14
    margin_inner_mm: float = 10
    margin_outer_mm: float = 10


class TypographyConfig(BaseModel):
    # DejaVu fonts ship in fonts-dejavu-core (~3 MB) and are bundled in our
    # Docker image. They cover Latin/Cyrillic/Greek with full diacritics —
    # solid default for DE/EN/FR. Override per profile if you bundle others.
    body_family: str = "DejaVu Serif"
    body_size_pt: float = 11
    body_leading_pt: float = 14.5
    heading_family: str = "DejaVu Sans"
    heading_h1_pt: float = 22
    heading_h2_pt: float = 16


class ColorConfig(BaseModel):
    enabled: bool = True
    palette: str = "muted"


class RenderingConfig(BaseModel):
    embed_bookmarks: bool = True
    hyperlinks: str = "short_url"
    image_max_width_pct: int = 100
    image_dither: str = "floyd_steinberg"


class DeliveryProfileConfig(BaseModel):
    default_channel: str = "filesystem"


class DeviceProfile(BaseModel):
    id: str
    display_name: str
    page: PageConfig
    typography: TypographyConfig = TypographyConfig()
    color: ColorConfig = ColorConfig()
    rendering: RenderingConfig = RenderingConfig()
    delivery: DeliveryProfileConfig = DeliveryProfileConfig()


def _resolve_dir(override: Path | None) -> Path:
    return override if override is not None else profiles_dir()


def load_profile(profile_id: str, override_dir: Path | None = None) -> DeviceProfile:
    directory = _resolve_dir(override_dir)
    path = directory / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Device profile not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return DeviceProfile.model_validate(data)


def list_profiles(override_dir: Path | None = None) -> list[DeviceProfile]:
    directory = _resolve_dir(override_dir)
    profiles = []
    for path in sorted(directory.glob("*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        profiles.append(DeviceProfile.model_validate(data))
    return profiles
