from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from lemonade._paths import templates_dir
from lemonade.render.profiles import DeviceProfile


def render_pdf(
    edition_json: dict,
    profile: DeviceProfile,
    output_path: Path,
    template: Path | None = None,
) -> Path:
    """Compile an edition into a PDF via Typst.

    JSON payloads are written to a sibling file beside the template instead of
    being passed via ``--input`` — Typst inputs are command-line arguments and
    a full edition can blow past ``ARG_MAX`` (~128 KiB on Linux). The template
    reads the payloads via ``json("edition.json")`` etc.
    """
    src_template = template or templates_dir() / "newspaper.typ"
    if not src_template.exists():
        raise FileNotFoundError(f"Template not found: {src_template}")

    # Copy the whole template tree (newspaper.typ + components/) into a temp
    # directory and write the JSON payloads next to it. That way `#import
    # "components/cover.typ"` keeps working and large payloads don't pollute
    # the repo.
    src_dir = src_template.parent
    with tempfile.TemporaryDirectory(prefix="lemonade-render-") as tmp:
        tmp_dir = Path(tmp)
        # Copy all .typ files (template + components/)
        for path in src_dir.rglob("*.typ"):
            rel = path.relative_to(src_dir)
            dst = tmp_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)

        edition_path = tmp_dir / "edition.json"
        profile_path = tmp_dir / "profile.json"
        edition_path.write_text(json.dumps(edition_json), encoding="utf-8")
        profile_path.write_text(profile.model_dump_json(), encoding="utf-8")

        tmp_template = tmp_dir / src_template.name

        cmd = ["typst", "compile", str(tmp_template), str(output_path)]

        # Ship our own fonts via TYPST_FONT_PATHS if any are bundled. Falls
        # back to system fonts otherwise.
        env = os.environ.copy()
        bundled_fonts = templates_dir() / "fonts"
        if bundled_fonts.is_dir():
            existing = env.get("TYPST_FONT_PATHS", "")
            env["TYPST_FONT_PATHS"] = (
                f"{bundled_fonts}{os.pathsep}{existing}" if existing else str(bundled_fonts)
            )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Typst compilation failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout[:1000]}\nstderr: {result.stderr[:1000]}"
            )
        return output_path
