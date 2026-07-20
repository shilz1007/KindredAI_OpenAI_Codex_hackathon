"""Domain models owned by the read-only public research feature."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ResearchAnswer:
    """A concise answer returned after a public Tavily search."""

    query: str
    answer: str
    provider: str
    researched_at: datetime

