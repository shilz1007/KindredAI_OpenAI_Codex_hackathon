"""Application port for the isolated Memory MCP persistence store."""

from datetime import datetime
from typing import Protocol

from kindred_ai.domain.memory import ConversationEntry, MemoryItem, UserProfile


class MemoryRepository(Protocol):
    """Persistence operations needed by Memory MCP use cases."""

    def get_user_profile(self, user_id: str) -> UserProfile | None: ...

    def add_memory(
        self, *, memory_id: str, user_id: str, content: str, category: str,
        source: str, importance: int, created_at: datetime,
    ) -> MemoryItem: ...

    def get_history(self, user_id: str, limit: int) -> list[ConversationEntry]: ...
