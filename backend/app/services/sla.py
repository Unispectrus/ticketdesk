from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..models import Priority, Status, Ticket, utcnow

SLA_HOURS = {Priority.urgent: 4, Priority.high: 8, Priority.medium: 24, Priority.low: 72}


def as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def due_date(priority: Priority, start: datetime | None = None) -> datetime:
    return (start or utcnow()) + timedelta(hours=SLA_HOURS[priority])


def mark_breaches(db: Session) -> int:
    """Flag still-active tickets past their SLA deadline. Idempotent; run by the worker."""
    result = db.execute(
        update(Ticket)
        .where(Ticket.status.in_([Status.open, Status.in_progress]), Ticket.sla_due_at < utcnow(), Ticket.sla_breached.is_(False))
        .values(sla_breached=True)
    )
    db.commit()
    return result.rowcount or 0
