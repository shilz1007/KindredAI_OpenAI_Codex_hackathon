"""Typed boundary for Master intent routing."""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class AgentRoute(BaseModel):
    """Validated routing decision returned by the Master router model."""

    model_config = ConfigDict(extra="forbid")

    agent: Literal["master", "companion", "guardian", "logistics", "research"]
    intent: Literal[
        "security_review",
        "security_inbox",
        "medication_supply",
        "medication_taken",
        "medication_status",
        "medication_replenishment",
        "general_companionship",
        "communication_call",
        "contact_assistance",
        "family_message",
        "family_birthday",
        "phone_book_contact",
        "household_request",
        "household_inventory",
        "household_purchase",
        "household_reminder",
        "unknown",
        "general_safety_guidance",
        "current_time",
        "research_query",
    ]
    language: Literal["en", "bn", "unknown"]
    medication_name: str | None
    medication_time: str | None = None
    medication_report: Literal["taken", "missed", "unknown"] = "unknown"
    quantity: int | None = Field(ge=1)
    household_item_name: str | None = None
    reminder_title: str | None = None
    remind_at: str | None = None
    contact_query: str | None = None
    message_content: str | None = None
    contact_display_name: str | None = None
    contact_phone_number: str | None = None


class AgentRouter(Protocol):
    """Classifies an utterance; it cannot call agents, MCPs, or databases."""

    def route(self, message: str) -> AgentRoute:
        """Return an architecture-approved routing decision."""
