from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lemonade._paths import templates_dir
from lemonade.render.profiles import DeviceProfile


def render_pdf(
    edition_json: dict,
    profile: DeviceProfile,
    output_path: Path,
    template: Path | None = None,
) -> Path:
    template = template or templates_dir() / "newspaper.typ"
    if not template.exists():
        raise FileNotFoundError(f"Template not found: {template}")

    result = subprocess.run(
        [
            "typst", "compile",
            "--input", f"edition={json.dumps(edition_json)}",
            "--input", f"profile={profile.model_dump_json()}",
            str(template),
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Typst compilation failed: {result.stderr}")
    return output_path
