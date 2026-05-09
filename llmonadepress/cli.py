from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import typer

app = typer.Typer(help="LLMonadePress — your personal AI newspaper.")
sources_app = typer.Typer(help="Manage configured sources.")
devices_app = typer.Typer(help="Manage device profiles.")
app.add_typer(sources_app, name="sources")
app.add_typer(devices_app, name="devices")


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
