"""Resolve paths to bundled data (device profiles, Typst templates).

Works in three modes:
1. Editable install / repo checkout: data lives at the repo root next to ``lemonade/``.
2. Wheel install: data is force-included into ``lemonade/_bundled/`` at build time.
3. Override: the env var ``LEMONADE_PROFILES_DIR`` / ``LEMONADE_TEMPLATES_DIR``
   takes precedence so users can ship their own profiles or templates.
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_ROOT.parent


def _find(env_var: str, name: str) -> Path:
    override = os.environ.get(env_var)
    if override:
        return Path(override)

    bundled = _PACKAGE_ROOT / "_bundled" / name
    if bundled.is_dir():
        return bundled

    return _REPO_ROOT / name


def profiles_dir() -> Path:
    return _find("LEMONADE_PROFILES_DIR", "device_profiles")


def templates_dir() -> Path:
    return _find("LEMONADE_TEMPLATES_DIR", "templates")
