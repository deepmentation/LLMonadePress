from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from llmonadepress.adapters.base import FetchedItem
from llmonadepress.adapters.rss import RSSAdapter
from llmonadepress.adapters.youtube import YouTubeAdapter
from llmonadepress.config import LLMonadePressConfig
from llmonadepress.llm.client import get_embeddings
from llmonadepress.models import Item, Source

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


async def _ingest_one(
    session: AsyncSession,
    source_type: str,
    identifier: str,
    config_dict: dict,
    fetch_coro,
    label: str,
) -> list[Item]:
    """Ingest a single source inside a savepoint so its failure doesn't poison
    the surrounding transaction. Commits the savepoint on success, rolls it
    back on failure."""
    try:
        async with session.begin_nested():
            source = await _ensure_source(session, source_type, identifier, config_dict)
            fetched = await fetch_coro(source)
            new_items = await _store_items(session, source, fetched)
            source.last_fetched = datetime.now(UTC)
            logger.info("%s %s: %d new items", label, identifier, len(new_items))
            return new_items
    except Exception:
        logger.exception("Failed to ingest %s source %s", label, identifier)
        return []


async def ingest(config: LLMonadePressConfig, session: AsyncSession) -> list[Item]:
    """Run the full ingestion pipeline: fetch from all sources, store, embed.

    Each source runs in its own savepoint — a single broken feed cannot
    abort the rest of the run.
    """
    since = datetime.now(UTC) - timedelta(hours=48)
    all_new_items: list[Item] = []

    rss_adapter = RSSAdapter()
    for src in config.rss:
        items = await _ingest_one(
            session,
            "rss",
            src.url,
            src.model_dump(),
            lambda _source, src=src: rss_adapter.fetch(src.url, src.model_dump(), since),
            "RSS",
        )
        all_new_items.extend(items)

    yt_adapter = YouTubeAdapter(asr_config=config.asr)
    for src in config.youtube:
        identifier = src.channel_id or src.channel_handle or ""
        items = await _ingest_one(
            session,
            "youtube_channel",
            identifier,
            src.model_dump(),
            lambda _source, src=src, identifier=identifier: yt_adapter.fetch(
                identifier, src.model_dump(), since
            ),
            "YouTube",
        )
        all_new_items.extend(items)

    try:
        await _embed_items(session, all_new_items, config.llm.embedding_model)
    except Exception:
        logger.exception("Failed to compute embeddings; continuing with what we have")

    await session.commit()
    return all_new_items
