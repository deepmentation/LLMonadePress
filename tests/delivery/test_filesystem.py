import pytest
from pathlib import Path
from lemonade.delivery.filesystem import FilesystemDelivery

@pytest.mark.asyncio
async def test_filesystem_delivery(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 test content")
    output_dir = tmp_path / "output"

    channel = FilesystemDelivery(output_dir)
    await channel.deliver(pdf, "2026-05-08", "remarkable_ppm")

    dest = output_dir / "remarkable_ppm_2026-05-08.pdf"
    assert dest.exists()
    assert dest.read_bytes() == b"%PDF-1.4 test content"

@pytest.mark.asyncio
async def test_filesystem_creates_directory(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "nested" / "output"

    channel = FilesystemDelivery(output_dir)
    await channel.deliver(pdf, "2026-05-08", "generic_a5")

    assert (output_dir / "generic_a5_2026-05-08.pdf").exists()
