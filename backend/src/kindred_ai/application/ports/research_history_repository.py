"""Persistence boundary for the small local public-research history."""

from typing import Protocol

from kindred_ai.domain.research import ResearchAnswer


class ResearchHistoryRepository(Protocol):
    """Stores the latest research answers independently from personal memory."""

    def initialize(self) -> None:
        """Create or migrate the local history store."""

    def add(self, answer: ResearchAnswer) -> ResearchAnswer:
        """Persist an answer and retain only the latest configured records."""

    def recent(self, *, limit: int = 20) -> list[ResearchAnswer]:
        """Return answers newest first."""

