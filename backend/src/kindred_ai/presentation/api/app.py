"""FastAPI application skeleton."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kindred_ai.application.health.service import initialize_health_service
from kindred_ai.application.inventory.service import initialize_inventory_service
from kindred_ai.application.memory.service import initialize_memory_service
from kindred_ai.application.security.service import initialize_security_service
from kindred_ai.application.communication.service import get_communication_service
from kindred_ai.config.agent_registry import initialize_agent_registry
from kindred_ai.presentation.api.routers.health import router as health_router
from kindred_ai.presentation.api.routers.guardian import router as guardian_router
from kindred_ai.presentation.api.routers.inventory import router as inventory_router
from kindred_ai.presentation.api.routers.memory import router as memory_router
from kindred_ai.presentation.api.routers.security import router as security_router
from kindred_ai.presentation.api.routers.companion import router as companion_router
from kindred_ai.presentation.api.routers.logistics import router as logistics_router
from kindred_ai.presentation.api.routers.master import router as master_router


def create_app() -> FastAPI:
    """Build the HTTP application and initialize local infrastructure."""
    initialize_agent_registry()
    initialize_health_service()
    initialize_inventory_service()
    initialize_memory_service()
    initialize_security_service()
    get_communication_service()
    app = FastAPI(title="Kindred AI Backend")
    allowed_origins = os.getenv("KINDRED_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
        # Vite chooses the next available port when 5173 is already occupied.
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(guardian_router, prefix="/api/v1")
    app.include_router(inventory_router, prefix="/api/v1")
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(security_router, prefix="/api/v1")
    app.include_router(companion_router, prefix="/api/v1")
    app.include_router(logistics_router, prefix="/api/v1")
    app.include_router(master_router, prefix="/api/v1")
    # TODO: Add authentication before exposing these testing endpoints externally.
    return app
