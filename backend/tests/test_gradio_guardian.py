"""Tests for the temporary Guardian Agent Gradio test harness."""

import os
import tempfile
import unittest
from pathlib import Path

from kindred_ai.agents.master import MasterAgent
from kindred_ai.application.ports.agent_router import AgentRoute
from kindred_ai.application.health.service import get_health_service
from kindred_ai.application.inventory.service import get_inventory_service
from kindred_ai.application.security.service import get_security_service
from kindred_ai.application.guardian import get_guardian_agent


class GradioGuardianTests(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        root = Path(self._directory.name)
        os.environ["KINDRED_HEALTH_DB_PATH"] = str(root / "health.sqlite3")
        os.environ["KINDRED_INVENTORY_DB_PATH"] = str(root / "inventory.sqlite3")
        os.environ["KINDRED_SECURITY_DB_PATH"] = str(root / "security.sqlite3")
        os.environ["KINDRED_DISABLE_LLM"] = "true"
        for service in (get_health_service, get_inventory_service, get_security_service):
            service.cache_clear()

    def tearDown(self) -> None:
        for service in (get_health_service, get_inventory_service, get_security_service):
            service.cache_clear()
        for key in ("KINDRED_HEALTH_DB_PATH", "KINDRED_INVENTORY_DB_PATH", "KINDRED_SECURITY_DB_PATH", "KINDRED_DISABLE_LLM"):
            os.environ.pop(key, None)
        self._directory.cleanup()

    def test_master_routes_guardian_workflows_to_a_conversation_model(self) -> None:
        class FakeConversationModel:
            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                return specialist_context

        class FakeRouter:
            def route(self, message: str) -> AgentRoute:
                lowered = message.lower()
                if "days" in lowered or "supply" in lowered:
                    return AgentRoute(agent="guardian", intent="medication_supply", language="en", medication_name=None, quantity=None)
                if "order" in lowered:
                    return AgentRoute(agent="guardian", intent="medication_replenishment", language="en", medication_name="Metformin", quantity=60)
                return AgentRoute(agent="guardian", intent="security_review", language="en", medication_name=None, quantity=None)

        master = MasterAgent(FakeConversationModel(), get_guardian_agent(), FakeRouter())
        self.assertIn("'risk_level': 'high'", master.respond("Urgent: send your gift card details now."))
        self.assertIn("'days_remaining': 6", master.respond("show medication supply"))
        self.assertIn("'days_remaining': 6", master.respond("How many days of Metformin do I have left?"))
        self.assertIn("'status': 'requested'", master.respond("confirm order Metformin 60"))
        self.assertIn("'status': 'requested'", master.respond("Please confirm an order for 60 Metformin tablets."))

    def test_master_delegates_to_companion_and_logistics_and_keeps_session_context(self) -> None:
        class RecordingConversationModel:
            def __init__(self) -> None:
                self.contexts: list[str] = []

            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                self.contexts.append(specialist_context)
                return f"reply to {user_message}"

        class FakeRouter:
            def route(self, message: str) -> AgentRoute:
                if "tea" in message.lower():
                    return AgentRoute(agent="logistics", intent="household_inventory", language="en", medication_name=None, quantity=None)
                if "call" in message.lower():
                    return AgentRoute(agent="companion", intent="communication_call", language="en", medication_name=None, quantity=None, contact_query="son")
                return AgentRoute(agent="companion", intent="general_companionship", language="en", medication_name=None, quantity=None)

        class FakeCompanion:
            def respond(self, message: str) -> str:
                return f"Companion context for {message}"

            def request_family_call(self, contact_query: str) -> dict[str, str]:
                return {"display_name": "Rahim", "relationship": "son"}

        class FakeLogistics:
            def household_inventory(self):
                return [{"item_name": "Jasmine tea", "reorder_needed": True}]

        model = RecordingConversationModel()
        master = MasterAgent(model, get_guardian_agent(), FakeRouter(), FakeCompanion(), FakeLogistics())
        self.assertEqual("reply to I feel lonely", master.respond("I feel lonely", session_id="browser-1"))
        self.assertEqual("reply to Do I need tea?", master.respond("Do I need tea?", session_id="browser-1"))
        self.assertIn("Companion context for I feel lonely", model.contexts[0])
        self.assertIn("Jasmine tea", model.contexts[1])
        self.assertIn("User: I feel lonely", model.contexts[1])
        self.assertIn("Assistant: reply to I feel lonely", model.contexts[1])
        self.assertEqual("reply to Call my son", master.respond("Call my son", session_id="browser-1"))
        self.assertIn("Call request recorded for Rahim (son)", model.contexts[2])
        master.clear_conversation("browser-1")
        master.respond("Fresh conversation", session_id="browser-1")
        self.assertNotIn("User: I feel lonely", model.contexts[3])
