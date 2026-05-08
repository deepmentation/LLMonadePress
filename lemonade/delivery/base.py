from __future__ import annotations

import abc
from pathlib import Path


class DeliveryChannel(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def deliver(self, pdf_path: Path, edition_date: str, device: str) -> None:
        ...
