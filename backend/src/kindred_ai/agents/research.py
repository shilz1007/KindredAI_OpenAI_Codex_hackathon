"""Research Agent: the only Kindred component allowed to consult Tavily."""

from datetime import UTC, datetime

from kindred_ai.application.ports.research_history_repository import ResearchHistoryRepository
from kindred_ai.application.ports.research_model import ResearchModel
from kindred_ai.domain.research import ResearchAnswer
from kindred_ai.infrastructure.observability import observation, record_output


class ResearchAgent:
    """Turns a public-information query into a persisted, concise answer."""

    def __init__(self, model: ResearchModel, history: ResearchHistoryRepository, instruction: str) -> None:
        self._model = model
        self._history = history
        self._instruction = instruction

    def research(self, query: str) -> ResearchAnswer:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("A research question is required.")
        with observation("agent.research", as_type="agent", input={"query": cleaned_query}, metadata={"agent": "research", "mcp_access": "tavily"}) as trace:
            answer = self._model.research(query=cleaned_query, instruction=self._instruction)
            result = self._history.add(ResearchAnswer(cleaned_query, answer, "tavily", datetime.now(UTC)))
            record_output(trace, {"answer": result.answer, "provider": result.provider})
            return result

    def recent_answers(self, *, limit: int = 20) -> list[ResearchAnswer]:
        return self._history.recent(limit=limit)

