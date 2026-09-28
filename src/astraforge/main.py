"""FastAPI application entry point."""

from fastapi import FastAPI

from astraforge import __version__
from astraforge.api import router
from astraforge.config import settings

app = FastAPI(title=settings.app_name, version=__version__)
app.include_router(router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a lightweight service health response."""
    return {"status": "ok", "app": settings.app_name, "version": __version__}
