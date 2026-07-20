"""Swagger-visible HTTP adapter for Memory MCP use cases."""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from kindred_ai.application.memory.service import MAX_HISTORY_LIMIT, get_memory_service

router = APIRouter(prefix="/memory", tags=["Memory MCP"])


class SaveMemoryRequest(BaseModel):
    """Input accepted when saving an approved memory item."""

    content: str = Field(examples=["Anita enjoys jasmine tea."])
    category: str = Field(default="general", examples=["preference"])
    source: str = Field(default="conversation", examples=["conversation"])
    importance: int = Field(default=1, ge=1, le=5, examples=[3])


@router.get("/profile")
def get_user_profile() -> dict[str, str | None]:
    """Get the internal demo user's Memory MCP profile."""
    return get_memory_service().get_user_profile().to_dict()


@router.post("/memories", status_code=status.HTTP_201_CREATED)
def save_memory(payload: SaveMemoryRequest) -> dict[str, str | int]:
    """Store an approved user-memory item."""
    try:
        memory = get_memory_service().save_memory(
            content=payload.content,
            category=payload.category,
            source=payload.source,
            importance=payload.importance,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return memory.to_dict()


@router.get("/history")
def retrieve_history(
    limit: int = Query(default=10, ge=1, le=MAX_HISTORY_LIMIT),
) -> list[dict[str, str]]:
    """Get recent conversation history, newest first."""
    return [entry.to_dict() for entry in get_memory_service().retrieve_history(limit=limit)]


@router.get("/memories")
def retrieve_memories(
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=MAX_HISTORY_LIMIT),
) -> list[dict[str, str | int]]:
    return [memory.to_dict() for memory in get_memory_service().retrieve_memories(category=category, limit=limit)]
