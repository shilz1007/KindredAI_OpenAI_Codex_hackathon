"""Pure domain models for the Memory MCP database."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UserProfile:
    """Personalization details owned by the Memory domain."""

    id: str
    preferred_name: str
    preferred_language: str
    timezone: str
    preferences: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "preferred_name": self.preferred_name,
            "preferred_language": self.preferred_language,
            "timezone": self.timezone,
            "preferences": self.preferences,
        }


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """A consented fact or preference saved from a conversation."""

    id: str
    content: str
    category: str
    source: str
    importance: int
    created_at: datetime

    def to_dict(self) -> dict[str, str | int]:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "source": self.source,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ConversationEntry:
    """A single bounded conversation-history entry."""

    id: str
    speaker: str
    content: str
    occurred_at: datetime

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "speaker": self.speaker,
            "content": self.content,
            "occurred_at": self.occurred_at.isoformat(),
        }
