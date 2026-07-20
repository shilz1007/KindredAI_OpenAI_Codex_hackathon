"""Short-lived, in-process conversation state for the development UI.

This is intentionally not a user-memory system. It is bounded session context
only; production state will need authenticated, encrypted persistence.
"""

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    role: str
    content: str


class InMemoryConversationState:
    """Keeps a small recent transcript per browser session without MCP access."""

    def __init__(self, *, max_sessions: int = 100, max_turns: int = 12) -> None:
        self._max_sessions = max_sessions
        self._max_turns = max_turns
        self._sessions: OrderedDict[str, list[ConversationTurn]] = OrderedDict()
        self._pending_actions: dict[str, dict[str, str]] = {}
        self._greeted_sessions: set[str] = set()
        self._daily_update_sessions: set[str] = set()
        self._lock = RLock()

    def recent_context(self, session_id: str) -> str:
        with self._lock:
            turns = self._sessions.get(session_id, [])
            if not turns:
                return "No earlier messages in this conversation."
            return "\n".join(f"{turn.role.title()}: {turn.content}" for turn in turns)

    def append_turn(self, session_id: str, *, role: str, content: str) -> None:
        with self._lock:
            turns = self._sessions.setdefault(session_id, [])
            turns.append(ConversationTurn(role=role, content=content))
            del turns[:-self._max_turns]
            self._sessions.move_to_end(session_id)
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._pending_actions.pop(session_id, None)
            self._greeted_sessions.discard(session_id)
            self._daily_update_sessions.discard(session_id)

    def claim_first_greeting(self, session_id: str) -> bool:
        """Return true exactly once for a conversation session."""
        with self._lock:
            if session_id in self._greeted_sessions:
                return False
            self._greeted_sessions.add(session_id)
            return True

    def claim_daily_update(self, session_id: str) -> bool:
        """Return true once when a completed task earns a gentle check-in."""
        with self._lock:
            if session_id in self._daily_update_sessions:
                return False
            self._daily_update_sessions.add(session_id)
            return True

    def pending_action(self, session_id: str) -> dict[str, str] | None:
        """Return the one short-lived action the session is completing."""
        with self._lock:
            action = self._pending_actions.get(session_id)
            return dict(action) if action else None

    def set_pending_action(self, session_id: str, action: dict[str, str]) -> None:
        with self._lock:
            self._pending_actions[session_id] = dict(action)

    def clear_pending_action(self, session_id: str) -> None:
        with self._lock:
            self._pending_actions.pop(session_id, None)
