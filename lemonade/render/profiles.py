from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class PageConfig(BaseModel):
    width_mm: float
    height_mm: float
    margin_top_mm: float = 12
    margin_bottom_mm: float = 14
    margin_inner_mm: float = 10
    margin_outer_mm: float = 10


class TypographyConfig(BaseModel):
    body_family: str = "Source Serif 4"
    body_size_pt: float = 11
    body_leading_pt: float = 14.5
    heading_family: str = "Inter"
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


PROFILES_DIR = Path(__file__).parent.parent.parent / "device_profiles"


def load_profile(profile_id: str, profiles_dir: Path | None = None) -> DeviceProfile:
    directory = profiles_dir or PROFILES_DIR
    path = directory / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Device profile not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return DeviceProfile.model_validate(data)


def list_profiles(profiles_dir: Path | None = None) -> list[DeviceProfile]:
    directory = profiles_dir or PROFILES_DIR
    profiles = []
    for path in sorted(directory.glob("*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        profiles.append(DeviceProfile.model_validate(data))
    return profiles
