from __future__ import annotations

import asyncio
import logging
import os
from datetime import date
from pathlib import Path

import typer

# Pipeline is the user's main feedback channel — show INFO logs by default
# unless they explicitly cranked it up or down via LEMONADE_LOG_LEVEL.
logging.basicConfig(
    level=os.environ.get("LEMONADE_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# LiteLLM is extremely chatty at INFO; keep it at WARNING.
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = typer.Typer(help="LLMonadePress — your personal AI newspaper.")
sources_app = typer.Typer(help="Manage configured sources.")
devices_app = typer.Typer(help="Manage device profiles.")
editions_app = typer.Typer(help="Inspect past editions.")
app.add_typer(sources_app, name="sources")
app.add_typer(devices_app, name="devices")
app.add_typer(editions_app, name="edition")


def _load_config(config_path: Path):
    from llmonadepress.config import load_config

    return load_config(config_path)


@app.command()
def run(
    config: Path = typer.Option("config.toml", "--config", "-c", help="Path to config.toml"),
    device: list[str] = typer.Option(None, "--device", "-d", help="Device profile(s) to render for"),
    no_deliver: bool = typer.Option(False, "--no-deliver", help="Skip delivery step"),
    date_str: str = typer.Option(None, "--date", help="Edition date (YYYY-MM-DD), defaults to today"),
):
    """Run the full pipeline: ingest, cluster, rank, write, render, deliver."""
    from llmonadepress.pipeline.orchestrate import run_pipeline

    cfg = _load_config(config)
    edition_date = date.fromisoformat(date_str) if date_str else None
    devices = device if device else None

    ids = asyncio.run(run_pipeline(cfg, edition_date=edition_date, devices=devices, deliver=not no_deliver))
    typer.echo(f"Created {len(ids)} edition(s): {[str(i) for i in ids]}")


@app.command()
def preview(
    config: Path = typer.Option("config.toml", "--config", "-c", help="Path to config.toml"),
    device: str = typer.Option(None, "--device", "-d", help="Device profile to render for"),
    date_str: str = typer.Option(None, "--date", help="Edition date (YYYY-MM-DD)"),
):
    """Render only (no delivery) and output the PDF path."""
    from llmonadepress.pipeline.orchestrate import run_pipeline

    cfg = _load_config(config)
    edition_date = date.fromisoformat(date_str) if date_str else None
    devices = [device] if device else None

    ids = asyncio.run(run_pipeline(cfg, edition_date=edition_date, devices=devices, deliver=False))
    if ids:
        typer.echo(f"Preview edition(s) created: {[str(i) for i in ids]}")
    else:
        typer.echo("No editions created.")


@app.command()
def init():
    """Initialize the database schema."""
    from llmonadepress.db import init_db

    asyncio.run(init_db())
    typer.echo("Database initialized.")


@sources_app.command("list")
def sources_list(
    config: Path = typer.Option("config.toml", "--config", "-c", help="Path to config.toml"),
):
    """List all configured sources from config.toml."""
    cfg = _load_config(config)
    typer.echo("RSS sources:")
    for src in cfg.rss:
        typer.echo(f"  - {src.url} (category: {src.category})")
    typer.echo("YouTube sources:")
    for src in cfg.youtube:
        ident = src.channel_id or src.channel_handle or "unknown"
        typer.echo(f"  - {ident} (category: {src.category})")
    if not cfg.rss and not cfg.youtube:
        typer.echo("  (no sources configured)")


@devices_app.command("list")
def devices_list():
    """List available device profiles."""
    from llmonadepress.render.profiles import list_profiles

    profiles = list_profiles()
    for p in profiles:
        typer.echo(f"  {p.id:25s} {p.display_name}")
    if not profiles:
        typer.echo("  (no device profiles found)")


@editions_app.command("show")
def edition_show(
    edition_date_str: str = typer.Argument(..., help="Edition date YYYY-MM-DD"),
    device: str = typer.Option(
        None, "--device", "-d", help="Device profile (default: first edition for that date)"
    ),
):
    """Inspect an existing edition: stage counts, ranker scores, items, sources.

    Answers questions like "why only 1 article from 50 transcripts?" by
    showing how many items were eligible, how the cluster collapsed them,
    what the ranker scored each cluster, and which stories shipped vs
    were dropped during writing.
    """
    from datetime import date as _date

    from sqlalchemy import select

    from llmonadepress.db import get_session_factory
    from llmonadepress.models import Edition, EditionItem, Item, Source

    try:
        edate = _date.fromisoformat(edition_date_str)
    except ValueError:
        typer.echo(f"Invalid date {edition_date_str!r}; expected YYYY-MM-DD", err=True)
        raise typer.Exit(1)

    async def _load() -> dict | None:
        async with get_session_factory()() as s:
            q = select(Edition).where(Edition.date == edate)
            if device:
                q = q.where(Edition.device == device)
            res = await s.execute(q.order_by(Edition.device))
            ed = res.scalars().first()
            if ed is None:
                return None

            # Items linked to this edition, with their source.
            ei_q = (
                select(EditionItem, Item, Source)
                .join(Item, EditionItem.item_id == Item.id)
                .join(Source, Item.source_id == Source.id)
                .where(EditionItem.edition_id == ed.id)
                .order_by(EditionItem.cluster_id, Item.title)
            )
            rows = (await s.execute(ei_q)).all()
            return {
                "edition": ed,
                "items": [(ei, it, src) for ei, it, src in rows],
            }

    data = asyncio.run(_load())
    if data is None:
        typer.echo(f"No edition found for {edate}{f' on {device}' if device else ''}", err=True)
        raise typer.Exit(1)

    ed: Edition = data["edition"]
    rows = data["items"]
    metrics = ed.metrics or {}
    payload = ed.json_payload or {}

    typer.echo(f"\n=== Edition {ed.date} · device={ed.device} · status={ed.status} ===")
    typer.echo(f"PDF: {ed.pdf_path or '(not rendered)'}")
    typer.echo(f"Delivered at: {ed.delivered_at or '—'}")

    typer.echo("\n--- Pipeline counts ---")
    typer.echo(f"  items eligible (after dedup): {metrics.get('items_eligible', '—')}")
    typer.echo(
        f"  clusters: {metrics.get('clusters_total', '—')} "
        f"(singletons: {metrics.get('clusters_singletons', '—')}, "
        f"top sizes: {metrics.get('cluster_sizes_top', '—')})"
    )
    typer.echo(
        f"  ranker returned: {metrics.get('ranker_returned', '—')} / "
        f"max_stories={metrics.get('ranker_max_stories', '—')}"
    )
    typer.echo(
        f"  stories written: {metrics.get('stories_written', '—')} "
        f"(dropped during write: {metrics.get('stories_dropped_in_write', '—')})"
    )

    rank_entries = metrics.get("rank_entries") or []
    if rank_entries:
        typer.echo("\n--- Ranker scores ---")
        for e in rank_entries:
            typer.echo(
                f"  cluster={e.get('cluster_id')}  "
                f"score={e.get('score')}  "
                f"rel={e.get('relevance')} nov={e.get('novelty')} "
                f"dep={e.get('depth')} brd={e.get('breadth')}  "
                f"sources={e.get('source_count')}"
            )
            if e.get("reason"):
                typer.echo(f"    reason: {e['reason']}")

    if rows:
        # Group items by cluster_id from edition_items
        from collections import defaultdict

        by_cluster: dict[str, list] = defaultdict(list)
        for ei, it, src in rows:
            by_cluster[ei.cluster_id or "(unclustered)"].append((it, src))

        # Try to align stories with clusters using metrics + payload order.
        all_stories = []
        if "lead_story" in payload:
            all_stories.append(payload["lead_story"])
        for sec in payload.get("sections", []):
            all_stories.extend(sec.get("stories", []))

        typer.echo("\n--- Items in this edition (grouped by cluster) ---")
        for cid, group in by_cluster.items():
            typer.echo(f"\n  Cluster {cid}  ({len(group)} item(s))")
            for it, src in group:
                published = it.published_at.strftime("%Y-%m-%d") if it.published_at else "—"
                kind = "📰" if src.type == "rss" else "🎥"
                meta = it.metadata_ or {}
                ts = meta.get("transcript_source", "")
                ts_note = f"  [transcript: {ts}]" if ts else ""
                typer.echo(f"    {kind} {published}  {(it.title or '')[:80]}{ts_note}")
                typer.echo(f"        {it.url}")

        if all_stories:
            typer.echo("\n--- Stories shipped in PDF ---")
            for st in all_stories:
                typer.echo(f"  ▸ {st.get('headline', '')}")
                if st.get("deck"):
                    typer.echo(f"    {st['deck']}")
    else:
        typer.echo("\n  (no items linked to this edition)")


@app.command("email-test")
def email_test(
    config: Path = typer.Option("config.toml", "--config", "-c", help="Path to config.toml"),
):
    """Send a test email via configured SMTP settings."""
    import aiosmtplib
    from email.message import EmailMessage

    from llmonadepress.config import SMTPSettings

    cfg = _load_config(config)
    smtp = SMTPSettings()

    if not smtp.host:
        typer.echo("SMTP not configured. Set LEMONADE_SMTP_* environment variables.", err=True)
        raise typer.Exit(1)

    msg = EmailMessage()
    msg["From"] = f"{cfg.delivery.email.from_name} <{smtp.from_addr}>"
    msg["To"] = ", ".join(cfg.delivery.email.to) if cfg.delivery.email.to else smtp.from_addr
    msg["Subject"] = "LLMonadePress — Test Email"
    msg.set_content("This is a test email from LLMonadePress. If you see this, SMTP is working.")

    async def _send():
        async with aiosmtplib.SMTP(
            hostname=smtp.host,
            port=smtp.port,
            use_tls=smtp.port == 465,
            start_tls=smtp.port == 587,
        ) as client:
            await client.login(smtp.user, smtp.password)
            await client.send_message(msg)

    asyncio.run(_send())
    typer.echo("Test email sent successfully.")


if __name__ == "__main__":
    app()
