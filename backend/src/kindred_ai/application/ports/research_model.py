"""Port for the single approved live-public-information provider."""

from typing import Protocol


class ResearchModel(Protocol):
    """Searches public information without access to Kindred personal data."""

    def research(self, *, query: str, instruction: str) -> str:
        """Return one concise, user-ready answer for a public factual query."""

