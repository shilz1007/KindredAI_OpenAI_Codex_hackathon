"""Tests for isolated live-research orchestration without spending Tavily credits."""

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from kindred_ai.agents.master import MasterAgent
from kindred_ai.agents.research import ResearchAgent
from kindred_ai.application.ports.agent_router import AgentRoute
from kindred_ai.domain.research import ResearchAnswer
from kindred_ai.infrastructure.openai.tavily_research import TavilyResearchError, TavilyResearchModel, UnavailableResearchModel
from kindred_ai.infrastructure.research.sqlite_repository import SqliteResearchHistoryRepository


class FakeResearchModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def research(self, *, query: str, instruction: str) -> str:
        self.calls.append((query, instruction))
        return "The library is open until five this afternoon."


class FakeResponse:
    output_text = "It will be **sunny** tomorrow."
    usage = None


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeResponse()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class ResearchRoute:
    def route(self, message: str) -> AgentRoute:
        return AgentRoute(
            agent="research", intent="research_query", language="en",
            medication_name=None, quantity=None, household_item_name=None, reminder_title=None,
            remind_at=None, contact_query=None, message_content=None,
            contact_display_name=None, contact_phone_number=None,
        )


class NoopGuardian:
    pass


class NoopConversationModel:
    def respond(self, **kwargs) -> str:
        raise AssertionError("Research answers should not be rewritten by the Master model.")


class ResearchAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.repository = SqliteResearchHistoryRepository(Path(self._temporary_directory.name) / "research.sqlite3")
        self.repository.initialize()

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_research_persists_a_concise_answer(self) -> None:
        model = FakeResearchModel()
        agent = ResearchAgent(model, self.repository, "Research only.")

        result = agent.research("When does the library close today?")

        self.assertEqual("tavily", result.provider)
        self.assertEqual("The library is open until five this afternoon.", result.answer)
        self.assertEqual([result], agent.recent_answers())
        self.assertEqual("Research only.", model.calls[0][1])

    def test_history_keeps_only_twenty_newest_answers(self) -> None:
        base_time = datetime(2026, 7, 20, tzinfo=UTC)
        for index in range(22):
            self.repository.add(ResearchAnswer(f"question {index}", f"answer {index}", "tavily", base_time + timedelta(seconds=index)))

        answers = self.repository.recent()

        self.assertEqual(20, len(answers))
        self.assertEqual("question 21", answers[0].query)
        self.assertEqual("question 2", answers[-1].query)

    def test_master_delegates_a_research_route_only_to_research_agent(self) -> None:
        agent = ResearchAgent(FakeResearchModel(), self.repository, "Research only.")
        master = MasterAgent(NoopConversationModel(), NoopGuardian(), ResearchRoute(), research=agent)

        reply = master.respond("What is the weather in Oslo tomorrow?")

        self.assertEqual("The library is open until five this afternoon.", reply)

    def test_remote_mcp_adapter_uses_tavily_with_read_only_defaults(self) -> None:
        client = FakeOpenAIClient()
        model = TavilyResearchModel(api_key="openai-test", tavily_api_key="secret key", model="gpt-5.1", client=client)

        result = model.research(query="Weather in Oslo", instruction="Research only.")

        self.assertEqual("It will be sunny tomorrow.", result)
        tool = client.responses.kwargs["tools"][0]
        self.assertEqual("mcp", tool["type"])
        self.assertEqual("tavily", tool["server_label"])
        self.assertEqual("never", tool["require_approval"])
        self.assertIn("tavilyApiKey=secret%20key", tool["server_url"])
        self.assertNotIn("secret key", tool["server_url"])

    def test_missing_tavily_configuration_has_a_safe_error(self) -> None:
        with self.assertRaisesRegex(TavilyResearchError, "not configured"):
            UnavailableResearchModel().research(query="Weather in Oslo", instruction="Research only.")


if __name__ == "__main__":
    unittest.main()
