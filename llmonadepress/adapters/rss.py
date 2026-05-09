from __future__ import annotations

from datetime import datetime, UTC
from email.utils import parsedate_to_datetime

import feedparser
import httpx
from trafilatura import extract

from llmonadepress.adapters.base import FetchedItem, SourceAdapter


class RSSAdapter(SourceAdapter):
    async def fetch(self, identifier: str, config: dict, since: datetime) -> list[FetchedItem]:
        feed = feedparser.parse(identifier)
        items = []
        for entry in feed.entries:
            published = self._parse_date(entry)
            if published and published < since:
                continue

            text = self._extract_text(entry)
            if config.get("follow_links") and text and len(text) < 500:
                text = await self._fetch_fulltext(entry.get("link", "")) or text

            items.append(FetchedItem(
                external_id=entry.get("id") or entry.get("link", ""),
                url=entry.get("link", ""),
                title=entry.get("title"),
                author=entry.get("author"),
                published_at=published,
                raw_text=text,
                metadata={"source_type": "rss"},
            ))
        return items

    def _parse_date(self, entry) -> datetime | None:
        for field in ("published", "updated"):
            val = entry.get(field)
            if val:
                try:
                    return parsedate_to_datetime(val).astimezone(UTC)
                except Exception:
                    pass
            parsed = entry.get(f"{field}_parsed")
            if parsed:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(mktime(parsed), tz=UTC)
                except Exception:
                    pass
        return None

    def _extract_text(self, entry) -> str | None:
        content_list = entry.get("content")
        if content_list:
            return content_list[0].get("value", "")
        return entry.get("summary")

    async def _fetch_fulltext(self, url: str) -> str | None:
        if not url:
            return None
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return extract(resp.text)
        except Exception:
            return None
