import pytest
from pathlib import Path
from llmonadepress.render.profiles import load_profile, list_profiles, DeviceProfile

PROFILES_DIR = Path(__file__).parent.parent.parent / "device_profiles"

def test_load_remarkable_ppm():
    p = load_profile("remarkable_ppm", PROFILES_DIR)
    assert p.id == "remarkable_ppm"
    assert p.page.width_mm == 107.8
    assert p.color.enabled is True

def test_load_kindle_paperwhite():
    p = load_profile("kindle_paperwhite", PROFILES_DIR)
    assert p.id == "kindle_paperwhite"
    assert p.color.enabled is False

def test_load_all_profiles():
    profiles = list_profiles(PROFILES_DIR)
    assert len(profiles) == 6
    ids = {p.id for p in profiles}
    assert "remarkable_ppm" in ids
    assert "generic_a5" in ids

def test_profile_not_found():
    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent", PROFILES_DIR)
