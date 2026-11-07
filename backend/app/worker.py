"""Background worker: flags SLA breaches every minute. Run: python -m app.worker"""
import logging
import time

from .database import SessionLocal
from .services.sla import mark_breaches

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ticketdesk.worker")

INTERVAL_SECONDS = 60


def run_once() -> int:
    with SessionLocal() as db:
        return mark_breaches(db)


if __name__ == "__main__":
    log.info("SLA worker started")
    while True:
        try:
            n = run_once()
            if n:
                log.info("Flagged %d newly breached tickets", n)
        except Exception:  # noqa: BLE001
            log.exception("SLA check failed")
        time.sleep(INTERVAL_SECONDS)
