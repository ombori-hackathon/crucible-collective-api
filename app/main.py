"""Main FastAPI application for The Crucible TCG backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import Base, engine
from app.logging_config import (
    generate_request_id,
    get_logger,
    request_id_ctx,
    setup_logging,
)
from app.models import Inventory, Item, User  # noqa: F401 - needed for table creation
from app.routers import fuse, loot, sell, stash

# Initialize logging
setup_logging(level=logging.INFO)
logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to each request context."""

    async def dispatch(self, request: Request, call_next):
        request_id = generate_request_id()
        token = request_id_ctx.set(request_id)

        logger.info(f"{request.method} {request.url.path}")

        try:
            response = await call_next(request)
            logger.info(f"Response status: {response.status_code}")
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            logger.error(f"Request failed: {type(e).__name__}: {e}")
            raise
        finally:
            request_id_ctx.reset(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("Starting The Crucible API...")

    # Create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    yield

    logger.info("Shutting down The Crucible API...")


app = FastAPI(
    title="The Crucible TCG API",
    description="Backend API for The Crucible generative trading card game",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middlewares
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(loot.router)
app.include_router(fuse.router)
app.include_router(stash.router)
app.include_router(sell.router)


@app.get("/")
async def root():
    """Root endpoint."""
    logger.debug("Root endpoint called")
    return {
        "message": "The Crucible TCG API is running!",
        "docs": "/docs",
        "endpoints": {
            "loot": "GET /loot?userid=1 - Get 4 random materials",
            "fuse": "POST /fuse - Combine materials (coming soon)",
            "stash": "GET /stash?userid=1 - View inventory (coming soon)",
            "sell": "POST /sell - Sell items (coming soon)",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
