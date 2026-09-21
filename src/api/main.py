"""
FastAPI application factory.

Sets up the application with CORS, lifespan events, and route registration.
# v0.1.1
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    from src.data.database import init_db

    if os.getenv("APP_ENV") == "development":
        await init_db()  # Auto-create tables in dev

    yield

    # Shutdown
    from src.data.database import dispose_db

    await dispose_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Supplier Performance Agent",
        description=(
            "AI agent that tracks supplier performance across quality, pricing, "
            "delivery, communication, and reliability."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from src.api.routes.chat import router as chat_router
    from src.api.routes.upload import router as upload_router
    from src.api.routes.scorecards import router as scorecards_router
    from src.api.routes.alerts import router as alerts_router
    from src.api.routes.suppliers import router as suppliers_router
    from src.api.routes.config import router as config_router
    from src.api.routes.email import router as email_router

    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(upload_router, prefix="/api", tags=["Upload"])
    app.include_router(scorecards_router, prefix="/api", tags=["Scorecards"])
    app.include_router(alerts_router, prefix="/api", tags=["Alerts"])
    app.include_router(suppliers_router, prefix="/api", tags=["Suppliers"])
    app.include_router(config_router, prefix="/api", tags=["Config"])
    app.include_router(email_router, prefix="/api", tags=["Email"])

    @app.get("/health", tags=["Health"])
    @app.get("/api/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}

    return app


# Application instance (used by uvicorn)
app = create_app()
