"""Use cases for the Memory MCP demo-user MVP."""

from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

from kindred_ai.application.ports.memory_repository import MemoryRepository
from kindred_ai.domain.memory import ConversationEntry, MemoryItem, UserProfile
from kindred_ai.infrastructure.memory.sqlite_repository import SqliteMemoryRepository

DEMO_USER_ID = "demo-user"
MAX_HISTORY_LIMIT = 100


class MemoryService:
    """Coordinates memory use cases without exposing SQL to MCP transports."""

    def __init__(self, repository: MemoryRepository) -> None:
        self._repository = repository

    def get_user_profile(self) -> UserProfile:
        """Return the profile for the internal demo user."""
        profile = self._repository.get_user_profile(DEMO_USER_ID)
        if profile is None:
            raise RuntimeError("The Memory MCP demo profile has not been initialized.")
        return profile

    def save_memory(
        self, *, content: str, category: str, source: str, importance: int,
    ) -> MemoryItem:
        """Persist a non-empty consented memory item with bounded importance."""
        if not content.strip():
            raise ValueError("Memory content cannot be empty.")
        if not 1 <= importance <= 5:
            raise ValueError("Memory importance must be between 1 and 5.")
        return self._repository.add_memory(
            memory_id=str(uuid4()), user_id=DEMO_USER_ID, content=content.strip(),
            category=category.strip() or "general", source=source.strip() or "conversation",
            importance=importance, created_at=datetime.now(UTC),
        )

    def retrieve_history(self, *, limit: int) -> list[ConversationEntry]:
        """Return recent history within a safe bounded request limit."""
        if not 1 <= limit <= MAX_HISTORY_LIMIT:
            raise ValueError(f"History limit must be between 1 and {MAX_HISTORY_LIMIT}.")
        return self._repository.get_history(DEMO_USER_ID, limit)

    def retrieve_memories(self, *, category: str | None = None, limit: int = 50) -> list[MemoryItem]:
        """Return saved personal facts for a bounded, approved read path."""
        if not 1 <= limit <= MAX_HISTORY_LIMIT:
            raise ValueError(f"Memory limit must be between 1 and {MAX_HISTORY_LIMIT}.")
        return self._repository.get_memories(DEMO_USER_ID, category=category.strip() if category else None, limit=limit)


@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    """Create and initialize the configured Memory MCP service once per process."""
    repository = SqliteMemoryRepository.from_environment()
    repository.initialize()
    return MemoryService(repository)


def initialize_memory_service() -> None:
    """Eagerly initialize Memory MCP persistence during application startup."""
    get_memory_service()
