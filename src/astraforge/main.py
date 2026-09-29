"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from astraforge import __version__
from astraforge.api import job_manager, router
from astraforge.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    job_manager.start()
    try:
        yield
    finally:
        await job_manager.stop()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
app.include_router(router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a lightweight service health response."""
    return {"status": "ok", "app": settings.app_name, "version": __version__}
