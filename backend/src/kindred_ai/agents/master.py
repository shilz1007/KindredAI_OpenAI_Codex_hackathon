"""Master Agent, the sole user-facing conversational coordinator."""

import re
from typing import Any

from kindred_ai.agents.guardian import GuardianAgent
from kindred_ai.agents.companion import CompanionAgent
from kindred_ai.agents.logistics import LogisticsAgent
from kindred_ai.application.ports.conversation_model import ConversationModel
from kindred_ai.application.ports.agent_router import AgentRoute, AgentRouter
from kindred_ai.application.conversation_state import InMemoryConversationState
from kindred_ai.infrastructure.observability import observation, record_output


class MasterAgent:
    """Routes Guardian workflows deterministically and speaks through a model."""

    def __init__(self, conversation_model: ConversationModel, guardian: GuardianAgent, router: AgentRouter, companion: CompanionAgent | None = None, logistics: LogisticsAgent | None = None, conversation_state: InMemoryConversationState | None = None) -> None:
        self._conversation_model = conversation_model
        self._guardian = guardian
        self._router = router
        self._companion = companion
        self._logistics = logistics
        self._conversation_state = conversation_state or InMemoryConversationState()

    def respond(self, message: str, *, session_id: str = "default") -> str:
        """Return an English reply informed by recent session and specialist context."""
        if not message.strip():
            raise ValueError("Message cannot be empty.")
        cleaned = message.strip()
        with observation("master.conversation", as_type="agent", input={"message": cleaned}, metadata={"session_id": session_id, "feature": "conversation"}) as trace:
            prior_context = self._conversation_state.recent_context(session_id)
            specialist_context = self._route_to_specialist(cleaned)
            reply = self._conversation_model.respond(
            instruction=(
                "You are the Kindred AI Master Agent, speaking warmly and clearly to an older adult. "
                "You are the only conversational agent. Use the specialist result below as factual context. "
                "Do not invent medication, order, or security facts. If a security alert exists, advise the user "
                "not to share sensitive details and to contact a trusted person. Continue the English conversation naturally. "
                "Keep the reply concise."
            ),
            user_message=cleaned,
            specialist_context=f"Recent conversation:\n{prior_context}\n\nSpecialist result:\n{specialist_context}",
            )
            self._conversation_state.append_turn(session_id, role="user", content=cleaned)
            self._conversation_state.append_turn(session_id, role="assistant", content=reply)
            record_output(trace, {"reply": reply})
            return reply

    def clear_conversation(self, session_id: str) -> None:
        """Remove one temporary browser session from the in-memory transcript."""
        self._conversation_state.clear(session_id)

    def get_specialist_context(self, message: str) -> str:
        """Run the approved specialist workflow without generating a user-facing reply.

        The Realtime voice adapter uses this boundary when the Master model calls
        its Guardian consultation tool.  The adapter never receives direct MCP
        access.
        """
        if not message.strip():
            raise ValueError("Message cannot be empty.")
        return self._route_to_specialist(message.strip())

    def _route_to_specialist(self, message: str) -> str:
        route = self._router.route(message)
        with observation(f"agent.{route.agent}", as_type="agent", input={"intent": route.intent}, metadata={"agent": route.agent, "intent": route.intent}) as agent_trace:
            result = self._execute_route(route, message)
            record_output(agent_trace, result)
            return result

    def _execute_route(self, route: AgentRoute, message: str) -> str:
        if route.agent == "master":
            return "General safety guidance only. Do not access Security MCP records or create an alert."
        if route.agent == "guardian":
            return self._route_guardian(route, message)
        if route.agent == "companion":
            return self._route_companion(route, message)
        if route.agent == "logistics":
            return self._route_logistics(route, message)
        return "No specialist workflow is available for this request."

    def _route_guardian(self, route: AgentRoute, message: str) -> str:
        if route.intent == "security_inbox":
            return f"Stored phone messages (newest first): {self._guardian.phone_messages()}"
        if route.intent == "medication_supply":
            return f"Medication supply: {self._guardian.medication_supply()}"
        if route.intent == "medication_replenishment":
            if not self._is_explicit_purchase_confirmation(message):
                return "A medication refill requires explicit confirmation before it can be requested."
            if route.medication_name and route.quantity:
                request = self._guardian.request_medication_replenishment(
                    medication_name=route.medication_name.title(), quantity=route.quantity, user_confirmed=True,
                )
                return f"Confirmed replenishment request: {request}"
        result: dict[str, Any] = self._guardian.analyze_message(message)
        return f"Guardian safety result: {result}"

    def _route_companion(self, route: AgentRoute, message: str) -> str:
        if self._companion is None:
            return "Companion Agent is selected, but it is not available."
        if route.intent == "communication_call":
            if not route.contact_query:
                return "Who would you like to call? For example, say 'call my son' or 'call Sara'."
            request = self._companion.request_family_call(route.contact_query)
            return (
                f"Call request recorded for {request['display_name']} ({request['relationship']}). "
                "This prototype does not place a real phone call yet."
            )
        return self._companion.respond(message)

    def _route_logistics(self, route: AgentRoute, message: str) -> str:
        if self._logistics is None:
            return "Logistics Agent is selected, but it is not available."
        if route.intent == "household_purchase":
            if not self._is_explicit_purchase_confirmation(message):
                return "A household purchase requires explicit confirmation before it can be requested."
            if route.household_item_name and route.quantity:
                request = self._logistics.request_purchase(
                    item_name=route.household_item_name, quantity=route.quantity, user_confirmed=True,
                )
                return f"Confirmed household purchase request: {request}"
        if route.intent == "household_reminder":
            if route.reminder_title and route.remind_at:
                reminder = self._logistics.schedule_reminder(title=route.reminder_title, remind_at=route.remind_at)
                return f"Scheduled household reminder: {reminder}"
            return "Please provide a reminder title and a date and time with timezone."
        return f"Household inventory: {self._logistics.household_inventory()}"

    @staticmethod
    def _is_explicit_purchase_confirmation(message: str) -> bool:
        """Policy check: an LLM route alone cannot authorize a purchase."""
        return bool(re.search(r"\bconfirm(?:ed)?\b", message, flags=re.IGNORECASE))
