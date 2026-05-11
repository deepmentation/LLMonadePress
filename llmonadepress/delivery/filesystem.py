from __future__ import annotations

import shutil
from pathlib import Path

from llmonadepress.delivery.base import DeliveryChannel


class FilesystemDelivery(DeliveryChannel):
    name = "filesystem"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    async def deliver(self, pdf_path: Path, edition_date: str, device: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        dest = self.output_dir / f"{edition_date}_{device}.pdf"
        # Orchestrate happens to render directly into output_dir, so source
        # and destination can resolve to the same file. shutil.copy2 raises
        # SameFileError in that case — for filesystem delivery this is a
        # no-op (the file is already where the user wants it).
        if pdf_path.resolve() == dest.resolve():
            return
        shutil.copy2(pdf_path, dest)
