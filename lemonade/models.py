from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now_utc() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(Text)  # 'rss' | 'youtube_channel'
    identifier: Mapped[str] = mapped_column(Text)  # URL or Channel-ID
    display_name: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(default=True)
    last_fetched: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[Item]] = relationship(back_populates="source")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_text: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    fingerprint: Mapped[str | None] = mapped_column(Text)
    embedding = mapped_column(Vector(1024), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)

    source: Mapped[Source] = relationship(back_populates="items")
    edition_links: Mapped[list[EditionItem]] = relationship(back_populates="item")


class Edition(Base):
    __tablename__ = "editions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date)
    device: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)  # rendering | ready | delivered | failed
    json_payload: Mapped[dict | None] = mapped_column(JSONB)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict | None] = mapped_column(JSONB)

    item_links: Mapped[list[EditionItem]] = relationship(back_populates="edition")
    deliveries: Mapped[list[Delivery]] = relationship(back_populates="edition")


class EditionItem(Base):
    __tablename__ = "edition_items"

    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"), primary_key=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id"), primary_key=True)
    cluster_id: Mapped[str | None] = mapped_column(Text)
    rank: Mapped[int | None] = mapped_column()

    edition: Mapped[Edition] = relationship(back_populates="item_links")
    item: Mapped[Item] = relationship(back_populates="edition_links")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"))
    channel: Mapped[str] = mapped_column(Text)  # remarkable | filesystem | email
    target: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)  # pending | success | failed
    error: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)

    edition: Mapped[Edition] = relationship(back_populates="deliveries")
