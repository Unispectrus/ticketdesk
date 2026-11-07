import logging
import smtplib
from email.message import EmailMessage

from ..config import settings

log = logging.getLogger("ticketdesk.email")


def send_email(to: str, subject: str, body: str) -> None:
    """Sends via SMTP if configured, otherwise logs (dev mode). Never raises into the request."""
    if not settings.smtp_host:
        log.info("EMAIL to=%s subject=%s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.email_from, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
    except Exception:  # noqa: BLE001
        log.exception("Failed to send email to %s", to)
