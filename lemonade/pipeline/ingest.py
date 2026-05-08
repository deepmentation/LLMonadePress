from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from lemonade.adapters.base import FetchedItem
from lemonade.adapters.rss import RSSAdapter
from lemonade.adapters.youtube import YouTubeAdapter
from lemonade.config import LemonadeConfig
from lemonade.llm.client import get_embeddings
from lemonade.models import Item, Source

logger = logging.getLogger(__name__)

BATCH_SIZE = 32


async def _ensure_source(
    session: AsyncSession, source_type: str, identifier: str, config: dict
) -> Source:
    """Get or create a Source row."""
    result = await session.execute(
        select(Source).where(Source.type == source_type, Source.identifier == identifier)
    )
    source = result.scalar_one_or_none()
    if source is None:
        source = Source(type=source_type, identifier=identifier, config=config, enabled=True)
        session.add(source)
        await session.flush()
    return source


async def _store_items(
    session: AsyncSession, source: Source, fetched: list[FetchedItem]
) -> list[Item]:
    """Insert items with dedup on (source_id, external_id). Returns newly inserted Items."""
    new_items: list[Item] = []
    for fi in fetched:
        result = await session.execute(
            select(Item).where(
                Item.source_id == source.id, Item.external_id == fi.external_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            continue
        item = Item(
            source_id=source.id,
            external_id=fi.external_id,
            url=fi.url,
            title=fi.title,
            author=fi.author,
            published_at=fi.published_at,
            raw_text=fi.raw_text,
            metadata_=fi.metadata,
        )
        session.add(item)
        new_items.append(item)
    await session.flush()
    return new_items


async def _embed_items(
    session: AsyncSession, items: list[Item], model: str
) -> None:
    """Generate embeddings for items that lack them."""
    to_embed = [it for it in items if it.embedding is None and it.raw_text]
    for i in range(0, len(to_embed), BATCH_SIZE):
        batch = to_embed[i : i + BATCH_SIZE]
        texts = [it.raw_text[:8000] for it in batch]
        embeddings = await get_embeddings(texts, model=model)
        for item, emb in zip(batch, embeddings):
            item.embedding = emb
    await session.flush()


async def ingest(config: LemonadeConfig, session: AsyncSession) -> list[Item]:
    """Run the full ingestion pipeline: fetch from all sources, store, embed."""
    since = datetime.now(timezone.utc) - timedelta(hours=48)
    all_new_items: list[Item] = []

    rss_adapter = RSSAdapter()
    for src in config.rss:
        try:
            source = await _ensure_source(
                session, "rss", src.url, src.model_dump()
            )
            fetched = await rss_adapter.fetch(src.url, src.model_dump(), since)
            new_items = await _store_items(session, source, fetched)
            all_new_items.extend(new_items)
            source.last_fetched = datetime.now(timezone.utc)
            logger.info("RSS %s: %d new items", src.url, len(new_items))
        except Exception:
            logger.exception("Failed to ingest RSS source %s", src.url)

    yt_adapter = YouTubeAdapter()
    for src in config.youtube:
        identifier = src.channel_id or src.channel_handle or ""
        try:
            source = await _ensure_source(
                session, "youtube_channel", identifier, src.model_dump()
            )
            fetched = await yt_adapter.fetch(identifier, src.model_dump(), since)
            new_items = await _store_items(session, source, fetched)
            all_new_items.extend(new_items)
            source.last_fetched = datetime.now(timezone.utc)
            logger.info("YouTube %s: %d new items", identifier, len(new_items))
        except Exception:
            logger.exception("Failed to ingest YouTube source %s", identifier)

    # Embed all items that need embeddings (new + any previously missing)
    await _embed_items(session, all_new_items, config.llm.embedding_model)
    await session.commit()

    return all_new_items
