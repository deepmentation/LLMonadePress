from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lemonade.config import LemonadeConfig, SMTPSettings
from lemonade.db import get_session_factory
from lemonade.delivery.email import EmailDelivery
from lemonade.delivery.filesystem import FilesystemDelivery
from lemonade.delivery.remarkable import RemarkableDelivery
from lemonade.llm.client import LLMClient
from lemonade.models import Delivery, Edition, EditionItem, Item
from lemonade.pipeline.cluster import Cluster, cluster_items
from lemonade.pipeline.ingest import ingest
from lemonade.pipeline.rank import rank_clusters
from lemonade.pipeline.write import WrittenStory, write_edition
from lemonade.render.profiles import load_profile
from lemonade.render.typst_runner import render_pdf

logger = logging.getLogger(__name__)


def _build_edition_json(
    stories: list[WrittenStory], edition_date: date, device: str
) -> dict:
    return {
        "date": edition_date.isoformat(),
        "device": device,
        "stories": [
            {
                "headline": s.headline,
                "deck": s.deck,
                "body": s.body,
                "category": s.category,
                "sources": s.sources,
                "pull_quote": s.pull_quote,
            }
            for s in stories
        ],
    }


async def _deliver(
    config: LemonadeConfig,
    pdf_path: Path,
    edition_date: str,
    device: str,
    session: AsyncSession,
    edition: Edition,
) -> None:
    """Run all enabled delivery channels."""
    channels = []

    if config.delivery.filesystem.enabled:
        channels.append(
            FilesystemDelivery(output_dir=config.delivery.filesystem.output_dir)
        )

    if config.delivery.email.enabled:
        smtp = SMTPSettings()
        channels.append(
            EmailDelivery(
                host=smtp.host,
                port=smtp.port,
                user=smtp.user,
                password=smtp.password,
                from_addr=smtp.from_addr,
                from_name=config.delivery.email.from_name,
                to=config.delivery.email.to,
                subject_template=config.delivery.email.subject_template,
                include_summary=config.delivery.email.include_summary_in_body,
            )
        )

    if config.delivery.remarkable.enabled:
        channels.append(
            RemarkableDelivery(folder=config.delivery.remarkable.folder)
        )

    for ch in channels:
        delivery = Delivery(
            edition_id=edition.id,
            channel=ch.name,
            status="pending",
        )
        session.add(delivery)
        await session.flush()
        try:
            await ch.deliver(pdf_path, edition_date, device)
            delivery.status = "success"
            delivery.attempted_at = datetime.now(timezone.utc)
            logger.info("Delivered via %s", ch.name)
        except Exception as exc:
            delivery.status = "failed"
            delivery.error = str(exc)
            logger.exception("Delivery via %s failed", ch.name)


async def run_pipeline(
    config: LemonadeConfig,
    edition_date: date | None = None,
    devices: list[str] | None = None,
    deliver: bool = True,
) -> list[uuid.UUID]:
    """Main pipeline entry point: ingest -> cluster -> rank -> write -> render -> deliver."""
    edition_date = edition_date or date.today()
    devices = devices or config.delivery.devices
    date_str = edition_date.isoformat()

    session_factory = get_session_factory()
    edition_ids: list[uuid.UUID] = []

    async with session_factory() as session:
        # 1. Ingest
        await ingest(config, session)

        # 2. Gather items with embeddings
        result = await session.execute(
            select(Item).where(Item.embedding.isnot(None))
        )
        items = result.scalars().all()

        item_dicts = [
            {
                "id": str(it.id),
                "title": it.title or "",
                "text": it.raw_text or "",
                "url": it.url,
                "embedding": list(it.embedding) if it.embedding is not None else None,
                "source_type": (it.metadata_ or {}).get("source_type", ""),
            }
            for it in items
        ]

        # 3. Cluster
        clusters = cluster_items(item_dicts)
        if not clusters:
            logger.warning("No clusters produced — nothing to publish.")
            return []

        # 4. Rank
        llm = LLMClient(default_model=config.llm.ranker_model)
        ranked, _rank_resp = await rank_clusters(
            clusters,
            max_stories=config.user.max_stories,
            client=llm,
            model=config.llm.ranker_model,
        )

        # 5. Write
        writer_llm = LLMClient(default_model=config.llm.writer_model)
        stories, _write_resps = await write_edition(
            clusters,
            ranked,
            writer_llm,
            model=config.llm.writer_model,
            language=config.user.language,
        )

        # 6. Render + deliver per device
        for device_id in devices:
            profile = load_profile(device_id)
            edition_json = _build_edition_json(stories, edition_date, device_id)

            output_dir = Path(config.delivery.filesystem.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = output_dir / f"{device_id}_{date_str}.pdf"

            edition = Edition(
                date=edition_date,
                device=device_id,
                status="rendering",
                json_payload=edition_json,
            )
            session.add(edition)
            await session.flush()

            try:
                render_pdf(edition_json, profile, pdf_path)
                edition.pdf_path = str(pdf_path)
                edition.status = "ready"
            except Exception:
                edition.status = "failed"
                logger.exception("Render failed for %s", device_id)
                edition_ids.append(edition.id)
                continue

            # Link items to edition
            cluster_map = {c.id: c for c in clusters}
            for entry in ranked:
                cluster = cluster_map.get(entry["cluster_id"])
                if not cluster:
                    continue
                for item_id_str in cluster.item_ids:
                    link = EditionItem(
                        edition_id=edition.id,
                        item_id=uuid.UUID(item_id_str),
                        cluster_id=cluster.id,
                        rank=entry.get("rank"),
                    )
                    session.add(link)

            if deliver:
                await _deliver(config, pdf_path, date_str, device_id, session, edition)
                edition.delivered_at = datetime.now(timezone.utc)
                edition.status = "delivered"

            edition_ids.append(edition.id)

        await session.commit()

    return edition_ids
