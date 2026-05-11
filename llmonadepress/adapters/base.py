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
    async def fetch(
        self,
        identifier: str,
        config: dict,
        since: datetime,
        known_external_ids: set[str] | None = None,
    ) -> list[FetchedItem]:
        """Discover items for the given source.

        ``known_external_ids`` lets the caller pre-filter videos / articles
        already stored in the DB. Adapters with expensive per-item work
        (YouTube ASR, RSS fulltext fetch) MUST honour it: skip discovery
        entries whose external_id is in the set BEFORE doing any paid /
        slow work. The orchestrator passes this set so duplicate runs
        don't re-transcribe known videos.
        """
        ...
