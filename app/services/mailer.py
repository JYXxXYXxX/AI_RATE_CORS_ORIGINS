from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import Settings

logger = logging.getLogger(__name__)


class MailDeliveryError(RuntimeError):
    pass


def smtp_configured(settings: Settings) -> bool:
    return bool(
        settings.smtp_host
        and settings.smtp_from_email
        and settings.smtp_username
        and settings.smtp_password
    )


def send_email(
    *,
    settings: Settings,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    if not smtp_configured(settings):
        raise MailDeliveryError("smtp not configured")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = (
        f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        if settings.smtp_from_name
        else str(settings.smtp_from_email)
    )
    message["To"] = to_email
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as client:
                client.login(str(settings.smtp_username), str(settings.smtp_password))
                client.send_message(message)
            return

        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as client:
            client.ehlo()
            if settings.smtp_use_tls:
                client.starttls()
                client.ehlo()
            client.login(str(settings.smtp_username), str(settings.smtp_password))
            client.send_message(message)
    except Exception as exc:  # pragma: no cover - depends on environment SMTP
        logger.exception("failed to send email to %s", to_email)
        raise MailDeliveryError(str(exc)) from exc

