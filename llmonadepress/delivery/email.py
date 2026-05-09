from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from llmonadepress.delivery.base import DeliveryChannel


class EmailDelivery(DeliveryChannel):
    name = "email"

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        from_name: str,
        to: list[str],
        subject_template: str = "LLMonadePress — {date:%A, %d. %B %Y}",
        include_summary: bool = True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr
        self.from_name = from_name
        self.to = to
        self.subject_template = subject_template
        self.include_summary = include_summary

    async def deliver(self, pdf_path: Path, edition_date: str, device: str) -> None:
        date = datetime.strptime(edition_date, "%Y-%m-%d")
        msg = EmailMessage()
        msg["From"] = f"{self.from_name} <{self.from_addr}>"
        msg["To"] = ", ".join(self.to)
        msg["Subject"] = self.subject_template.format(date=date)
        msg.set_content(f"Deine LLMonadePress-Ausgabe vom {edition_date} liegt im Anhang.")

        with open(pdf_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=pdf_path.name,
            )

        async with aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            use_tls=self.port == 465,
            start_tls=self.port == 587,
        ) as client:
            await client.login(self.user, self.password)
            await client.send_message(msg)
