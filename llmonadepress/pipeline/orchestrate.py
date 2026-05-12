from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, UTC
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from urllib.parse import urlparse

from llmonadepress.config import LLMonadePressConfig, SMTPSettings
from llmonadepress.db import get_session_factory
from llmonadepress.delivery.email import EmailDelivery
from llmonadepress.delivery.filesystem import FilesystemDelivery
from llmonadepress.delivery.remarkable import RemarkableDelivery
from llmonadepress.llm.client import LLMClient
from llmonadepress.models import Delivery, Edition, EditionItem, Item, Source
from llmonadepress.pipeline.cluster import Cluster, cluster_items
from llmonadepress.pipeline.ingest import ingest
from llmonadepress.pipeline.rank import rank_clusters
from llmonadepress.pipeline.write import WrittenStory, write_edition
from llmonadepress.render.profiles import load_profile
from llmonadepress.render.typst_runner import render_pdf

logger = logging.getLogger(__name__)


async def _enrich_cluster_sources(
    session: AsyncSession, clusters: list[Cluster]
) -> None:
    """Attach authoritative source metadata to each cluster.

    Pulls (Item, Source) by id and builds a per-cluster ``sources`` list
    of dicts with title, url, domain, type, published_at, channel_name.
    This gives both the ranker (popularity / source-type breadth signal)
    and the renderer (real, non-hallucinated "weiterlesen" entries)
    something to work with.
    """
    all_ids = {iid for c in clusters for iid in c.item_ids}
    if not all_ids:
        return
    import uuid as _uuid

    rows = await session.execute(
        select(Item, Source).join(Source).where(Item.id.in_([_uuid.UUID(i) for i in all_ids]))
    )
    meta: dict[str, dict] = {}
    for item, source in rows.all():
        domain = urlparse(item.url).netloc.lower().removeprefix("www.")
        is_youtube = source.type == "youtube_channel"
        meta[str(item.id)] = {
            "item_id": str(item.id),
            "title": item.title or "",
            "url": item.url,
            "domain": domain,
            "type": "youtube" if is_youtube else "rss",
            "published_at": item.published_at.isoformat() if item.published_at else None,
            # For YouTube the author is the channel name; for RSS use the
            # source's display_name or fall back to the domain.
            "channel_name": (
                item.author if is_youtube else (source.display_name or domain)
            ),
        }

    for c in clusters:
        c.sources = [meta[i] for i in c.item_ids if i in meta]


def _story_dict(s: WrittenStory) -> dict:
    return {
        "headline": s.headline,
        "deck": s.deck,
        "body": s.body,
        "category": s.category,
        "sources": s.sources,
        "pull_quote": s.pull_quote,
    }


def _build_edition_json(
    stories: list[WrittenStory],
    edition_date: date,
    device: str,
    language: str,
    rss_count: int = 0,
    youtube_count: int = 0,
    qr_codes: bool = True,
) -> dict:
    """Assemble the edition payload consumed by templates/newspaper.typ.

    Schema (must stay in sync with templates):
      edition_date, device, language: scalars
      render: {qr_codes}
      lead_story: top-ranked story (or None)
      sections: list of {name, stories[]} grouped by category
      metadata: {sources_count: {rss, youtube}}
    """
    lead = stories[0] if stories else None
    rest = stories[1:] if stories else []

    by_category: dict[str, list[WrittenStory]] = {}
    for s in rest:
        by_category.setdefault(s.category or "General", []).append(s)

    sections = [
        {"name": name, "stories": [_story_dict(s) for s in items]}
        for name, items in by_category.items()
    ]

    payload: dict = {
        "edition_date": edition_date.isoformat(),
        "device": device,
        "language": language,
        "render": {"qr_codes": qr_codes},
        "sections": sections,
        "metadata": {
            "sources_count": {"rss": rss_count, "youtube": youtube_count},
        },
    }
    if lead is not None:
        payload["lead_story"] = _story_dict(lead)
    return payload


async def _deliver(
    config: LLMonadePressConfig,
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
        if not (smtp.host and smtp.user and smtp.password and smtp.from_addr):
            logger.warning(
                "Email delivery enabled but SMTP settings are incomplete "
                "(LEMONADE_SMTP_{HOST,USER,PASS,FROM} env vars). Skipping."
            )
        elif not config.delivery.email.to:
            logger.warning("Email delivery enabled but no recipients configured. Skipping.")
        else:
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
            delivery.attempted_at = datetime.now(UTC)
            logger.info("Delivered via %s", ch.name)
        except Exception as exc:
            delivery.status = "failed"
            delivery.error = str(exc)
            logger.exception("Delivery via %s failed", ch.name)


async def run_pipeline(
    config: LLMonadePressConfig,
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

        # 2. Gather items with embeddings, excluding anything already
        # delivered in a prior successful edition. Without this filter
        # the same story could be published every day until it falls out
        # of the source feeds.
        already_published = (
            select(EditionItem.item_id)
            .join(Edition, EditionItem.edition_id == Edition.id)
            .where(Edition.status.in_(("ready", "delivered")))
        )
        result = await session.execute(
            select(Item)
            .where(Item.embedding.isnot(None))
            .where(~Item.id.in_(already_published))
        )
        items = result.scalars().all()
        logger.info("Pipeline: %d eligible items (after cross-edition dedup)", len(items))

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

        # 3. Cluster + enrich with authoritative source metadata
        clusters = cluster_items(item_dicts)
        if not clusters:
            logger.warning("No clusters produced — nothing to publish.")
            return []
        await _enrich_cluster_sources(session, clusters)

        cluster_sizes = sorted([len(c.item_ids) for c in clusters], reverse=True)
        singletons = sum(1 for s in cluster_sizes if s == 1)
        logger.info(
            "Pipeline: %d clusters from %d items "
            "(largest=%d, singletons=%d, top sizes=%s)",
            len(clusters), len(items),
            cluster_sizes[0] if cluster_sizes else 0,
            singletons,
            cluster_sizes[:5],
        )

        # 4. Rank
        llm = LLMClient(default_model=config.llm.ranker_model)
        ranked, _rank_resp = await rank_clusters(
            clusters,
            max_stories=config.user.max_stories,
            client=llm,
            model=config.llm.ranker_model,
            language=config.user.language,
        )
        logger.info(
            "Pipeline: ranker returned %d/%d entries (max_stories=%d). "
            "Top scores: %s",
            len(ranked), len(clusters), config.user.max_stories,
            [
                f"{e.get('cluster_id', '?')}={e.get('score', '?')}"
                for e in ranked[:5]
            ],
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
        dropped_in_write = len(ranked) - len(stories)
        logger.info(
            "Pipeline: %d stories written (%d dropped during write)",
            len(stories), dropped_in_write,
        )

        # Metrics for this run, persisted on each edition below.
        run_metrics = {
            "items_eligible": len(items),
            "clusters_total": len(clusters),
            "clusters_singletons": singletons,
            "cluster_sizes_top": cluster_sizes[:10],
            "ranker_returned": len(ranked),
            "ranker_max_stories": config.user.max_stories,
            "stories_written": len(stories),
            "stories_dropped_in_write": dropped_in_write,
            # Per-cluster ranker scores so `lemonade edition show` can
            # explain why a story made it.
            "rank_entries": [
                {
                    "cluster_id": e.get("cluster_id"),
                    "relevance": e.get("relevance"),
                    "novelty": e.get("novelty"),
                    "depth": e.get("depth"),
                    "breadth": e.get("breadth"),
                    "score": e.get("score"),
                    "reason": e.get("reason"),
                    "source_count": next(
                        (len(c.sources) for c in clusters if c.id == e.get("cluster_id")),
                        None,
                    ),
                }
                for e in ranked
            ],
        }

        # 6. Render + deliver per device
        for device_id in devices:
            profile = load_profile(device_id)
            edition_json = _build_edition_json(
                stories,
                edition_date,
                device_id,
                language=config.user.language,
                rss_count=len(config.rss),
                youtube_count=len(config.youtube),
                qr_codes=config.render.qr_codes,
            )

            output_dir = Path(config.delivery.filesystem.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = output_dir / f"{date_str}_{device_id}.pdf"

            edition = Edition(
                date=edition_date,
                device=device_id,
                status="rendering",
                json_payload=edition_json,
                metrics=run_metrics,
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
                edition.delivered_at = datetime.now(UTC)
                edition.status = "delivered"

            edition_ids.append(edition.id)

        await session.commit()

    return edition_ids
