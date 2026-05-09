import uuid
from datetime import date, datetime

from llmonadepress.models import Delivery, Edition, EditionItem, Item, Source


def test_source_creation():
    s = Source(id=uuid.uuid4(), type="rss", identifier="https://example.com/feed.xml", config={})
    assert s.type == "rss"


def test_item_creation():
    i = Item(id=uuid.uuid4(), source_id=uuid.uuid4(), external_id="123", url="https://example.com")
    assert i.external_id == "123"


def test_edition_creation():
    e = Edition(id=uuid.uuid4(), date=date.today(), device="remarkable_ppm", status="rendering")
    assert e.status == "rendering"


def test_edition_item_creation():
    ei = EditionItem(edition_id=uuid.uuid4(), item_id=uuid.uuid4(), rank=1)
    assert ei.rank == 1


def test_delivery_creation():
    d = Delivery(id=uuid.uuid4(), edition_id=uuid.uuid4(), channel="email", status="pending")
    assert d.channel == "email"
