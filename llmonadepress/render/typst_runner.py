from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from llmonadepress._paths import templates_dir
from llmonadepress.render.profiles import DeviceProfile

logger = logging.getLogger(__name__)


def _iter_stories(edition_json: dict):
    """Yield every story dict in the edition (lead + section stories)."""
    lead = edition_json.get("lead_story")
    if lead:
        yield lead
    for section in edition_json.get("sections", []) or []:
        for story in section.get("stories", []) or []:
            yield story


def _generate_source_qrs(edition_json: dict, dest_dir: Path) -> None:
    """Render a QR PNG for every unique source URL in the edition into
    ``dest_dir`` and stamp the relative filename into each source dict.

    Reused per URL — multiple stories pointing at the same source share a
    file. Skipped entirely when ``edition.render.qr_codes`` is False so the
    user's opt-out is honoured. Failures (e.g. qrcode unavailable, weird URL)
    are logged and skipped silently; the template tolerates a missing
    ``qr_filename``.
    """
    render_cfg = edition_json.get("render") or {}
    if not render_cfg.get("qr_codes", True):
        return

    try:
        import qrcode
    except ImportError:
        logger.warning("qrcode library not installed; skipping QR generation")
        return

    seen: dict[str, str] = {}
    for story in _iter_stories(edition_json):
        for src in story.get("sources", []) or []:
            url = (src.get("url") or "").strip()
            if not url:
                continue
            if url not in seen:
                key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
                fname = f"qr_{key}.png"
                try:
                    img = qrcode.make(url, box_size=4, border=2)
                    img.save(dest_dir / fname)
                    seen[url] = fname
                except Exception:
                    logger.exception("QR generation failed for %s", url)
                    continue
            src["qr_filename"] = seen[url]


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

        # Generate QR PNGs for every source URL into the same temp dir,
        # so the template can reference them by relative filename.
        # Mutates edition_json in place (adds source.qr_filename) — fine
        # because we already own this rendering's copy of the dict.
        _generate_source_qrs(edition_json, tmp_dir)

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
