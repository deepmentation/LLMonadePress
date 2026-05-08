import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from lemonade.delivery.email import EmailDelivery

@pytest.fixture
def email_channel():
    return EmailDelivery(
        host="smtp.example.com",
        port=587,
        user="user",
        password="pass",
        from_addr="lemonade@example.com",
        from_name="Lemonade Daily",
        to=["reader@example.com"],
    )

@pytest.mark.asyncio
async def test_email_delivery(email_channel, tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    mock_smtp = AsyncMock()
    mock_smtp.__aenter__ = AsyncMock(return_value=mock_smtp)
    mock_smtp.__aexit__ = AsyncMock(return_value=False)

    with patch("lemonade.delivery.email.aiosmtplib.SMTP", return_value=mock_smtp):
        await email_channel.deliver(pdf, "2026-05-08", "kindle_paperwhite")
        mock_smtp.login.assert_called_once_with("user", "pass")
        mock_smtp.send_message.assert_called_once()
