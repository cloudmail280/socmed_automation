"""FastAPI entrypoint.

Run:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth import BasicAuthMiddleware
from app.config import get_settings
from app.database import init_db
from app.routers import products, schedule
from app.scheduler import shutdown as stop_scheduler
from app.scheduler import start as start_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="Socmed Automation", lifespan=lifespan)

_settings = get_settings()
if _settings.auth_username and _settings.auth_password:
    app.add_middleware(
        BasicAuthMiddleware,
        username=_settings.auth_username,
        password=_settings.auth_password,
    )

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(products.router)
app.include_router(schedule.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
