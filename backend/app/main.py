import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import admin, auth, tickets
from .worker import INTERVAL_SECONDS, run_once

log = logging.getLogger("ticketdesk.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = None
    if settings.inline_sla_worker:

        async def loop() -> None:
            while True:
                try:
                    await asyncio.to_thread(run_once)
                except Exception:  # noqa: BLE001
                    log.exception("SLA check failed")
                await asyncio.sleep(INTERVAL_SECONDS)

        task = asyncio.create_task(loop())
    yield
    if task:
        task.cancel()

app = FastAPI(title="TicketDesk API", version="1.0.0", description="Multi-tenant support ticketing system", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip().rstrip("/") for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(admin.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
