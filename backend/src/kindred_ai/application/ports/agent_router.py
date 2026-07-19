"""Typed boundary for Master intent routing."""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class AgentRoute(BaseModel):
    """Validated routing decision returned by the Master router model."""

    model_config = ConfigDict(extra="forbid")

    agent: Literal["master", "companion", "guardian", "logistics"]
    intent: Literal[
        "security_review",
        "medication_supply",
        "medication_replenishment",
        "general_companionship",
        "communication_call",
        "household_request",
        "household_inventory",
        "household_purchase",
        "household_reminder",
        "unknown",
        "general_safety_guidance",
    ]
    language: Literal["en", "bn", "unknown"]
    medication_name: str | None
    quantity: int | None = Field(ge=1)
    household_item_name: str | None = None
    reminder_title: str | None = None
    remind_at: str | None = None
    contact_query: str | None = None


class AgentRouter(Protocol):
    """Classifies an utterance; it cannot call agents, MCPs, or databases."""

    def route(self, message: str) -> AgentRoute:
        """Return an architecture-approved routing decision."""
