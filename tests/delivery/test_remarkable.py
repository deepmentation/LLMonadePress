import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
from lemonade.delivery.remarkable import RemarkableDelivery

@pytest.mark.asyncio
async def test_remarkable_delivery(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    channel = RemarkableDelivery(folder="Newspaper")
    with patch.object(channel, "_rmapi", new_callable=AsyncMock) as mock_rmapi:
        await channel.deliver(pdf, "2026-05-08", "remarkable_ppm")
        assert mock_rmapi.call_count == 3
        mock_rmapi.assert_any_call("mkdir", "-p", "/Newspaper/2026-05/")

@pytest.mark.asyncio
async def test_remarkable_rmapi_failure():
    channel = RemarkableDelivery()
    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
    with patch("lemonade.delivery.remarkable.asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="rmapi failed"):
            await channel._rmapi("put", "test.pdf", "/folder/")
