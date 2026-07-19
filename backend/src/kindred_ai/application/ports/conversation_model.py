"""Port for a user-facing conversational model."""

from typing import Protocol


class ConversationModel(Protocol):
    """Transforms Master context into a concise user-facing response."""

    def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str: ...
