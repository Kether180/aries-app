import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import engine
from app.middleware import RequestIdFilter, RequestIdMiddleware, SecurityHeadersMiddleware
from app.routers import articles, ask, news, research
from app.services.errors import UpstreamError

logger = logging.getLogger(__name__)

# Built Vue app. In production the API also serves the frontend, so it's one deployable service.
FRONTEND_DIST = (Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail loudly at startup rather than on the first request. Missing keys don't stop the app
    # (the UI still works for browsing stored results), but they are the first thing in the log.
    for name, value in [("OPENAI_API_KEY", settings.openai_api_key), ("GNEWS_API_KEY", settings.gnews_api_key)]:
        if not value:
            logger.warning("%s is not set: the feature that needs it will return 503", name)
    logger.info("database: %s", settings.sqlalchemy_url.split("@")[-1])  # host/db only, never credentials
    yield


# Database tables are managed by Alembic migrations: run `alembic upgrade head` before starting.
app = FastAPI(
    title="AriesNews API",
    version="0.1.0",
    description="Search news, summarise and score sentiment with OpenAI, and ask questions over the results.",
    lifespan=lifespan,
)

# Middleware runs in reverse order of registration: request ID is set first, so it's in every log line.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(UpstreamError)
def upstream_error_handler(request: Request, exc: UpstreamError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "service": exc.service})


@app.exception_handler(Exception)
def unhandled_error_handler(request: Request, exc: Exception):
    # Logged with the request ID so the client's X-Request-ID header leads straight to the traceback
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health", tags=["meta"])
def health():
    # The engine name (never the URL) makes a misconfigured DATABASE_URL visible from outside
    raw = os.environ.get("DATABASE_URL")
    if raw is None:
        state = "unset"
    elif not raw.strip():
        state = "empty"
    elif raw.startswith("${{"):
        state = "unresolved reference"
    else:
        state = raw.split(":", 1)[0][:12]  # scheme only, never credentials
    return {"status": "ok", "database": engine.dialect.name, "database_url": state}


app.include_router(news.router)
app.include_router(articles.router)
app.include_router(ask.router)
app.include_router(research.router)


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            # Unknown API routes get a JSON 404, not the frontend's index.html
            raise HTTPException(status_code=404, detail="Not found")
        file = (FRONTEND_DIST / path).resolve()
        # Only serve files inside dist (guards against ../ traversal); everything else is a client route
        if path and file.is_relative_to(FRONTEND_DIST) and file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")
