from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FetchedItem:
    external_id: str
    url: str
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    raw_text: str | None = None
    metadata: dict | None = None


class SourceAdapter(abc.ABC):
    @abc.abstractmethod
    async def fetch(self, identifier: str, config: dict, since: datetime) -> list[FetchedItem]:
        ...
