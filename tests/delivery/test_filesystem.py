import pytest
from pathlib import Path
from llmonadepress.delivery.filesystem import FilesystemDelivery

@pytest.mark.asyncio
async def test_filesystem_delivery(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4 test content")
    output_dir = tmp_path / "output"

    channel = FilesystemDelivery(output_dir)
    await channel.deliver(pdf, "2026-05-08", "remarkable_ppm")

    dest = output_dir / "2026-05-08_remarkable_ppm.pdf"
    assert dest.exists()
    assert dest.read_bytes() == b"%PDF-1.4 test content"

@pytest.mark.asyncio
async def test_filesystem_creates_directory(tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "nested" / "output"

    channel = FilesystemDelivery(output_dir)
    await channel.deliver(pdf, "2026-05-08", "generic_a5")

    assert (output_dir / "2026-05-08_generic_a5.pdf").exists()


@pytest.mark.asyncio
async def test_filesystem_handles_src_equals_dest(tmp_path):
    """Regression: orchestrate renders into output_dir directly, so the
    source PDF and the delivery destination resolve to the same file.
    shutil.copy2 raises SameFileError in that case — delivery should
    be a quiet no-op instead."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    pdf = output_dir / "2026-05-10_remarkable_ppm.pdf"
    pdf.write_bytes(b"%PDF-1.4 already in place")

    channel = FilesystemDelivery(output_dir)
    await channel.deliver(pdf, "2026-05-10", "remarkable_ppm")

    assert pdf.exists()
    assert pdf.read_bytes() == b"%PDF-1.4 already in place"
