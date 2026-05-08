from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from lemonade.delivery.base import DeliveryChannel


class RemarkableDelivery(DeliveryChannel):
    name = "remarkable"

    def __init__(self, folder: str = "Newspaper"):
        self.folder = folder

    async def deliver(self, pdf_path: Path, edition_date: str, device: str) -> None:
        if shutil.which("rmapi") is None:
            raise RuntimeError(
                "rmapi binary not found in PATH. Install ddvk/rmapi and run "
                "`rmapi` once to authenticate, or disable [delivery.remarkable] "
                "in config.toml."
            )
        target = f"/{self.folder}/{edition_date[:7]}/"
        await self._rmapi("mkdir", "-p", target)
        await self._rmapi("put", str(pdf_path), target)
        await self._rmapi("put", str(pdf_path), f"/{self.folder}/Latest.pdf")

    async def _rmapi(self, *args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            "rmapi", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"rmapi failed: {stderr.decode()}")
        return stdout.decode()
