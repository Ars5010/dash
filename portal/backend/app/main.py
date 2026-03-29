from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import create_app
from app.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = create_app()
app.router.lifespan_context = lifespan

