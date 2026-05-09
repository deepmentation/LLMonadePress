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
        shutil.copy2(pdf_path, dest)
