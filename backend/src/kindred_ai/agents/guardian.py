"""Guardian Agent orchestration over approved Health, Security, and Inventory services."""

from typing import Any

from kindred_ai.application.ports.conversation_model import ConversationModel
from kindred_ai.infrastructure.mcp_clients import HealthMcpClient, InventoryMcpClient, SecurityMcpClient


class GuardianAgent:
    """Coordinates prototype safety and medication-replenishment workflows."""

    def __init__(self, security: SecurityMcpClient, health: HealthMcpClient, inventory: InventoryMcpClient, conversation_model: ConversationModel | None = None) -> None:
        self._security = security
        self._health = health
        self._inventory = inventory
        self._conversation_model = conversation_model

    def analyze_message(self, message: str) -> dict[str, Any]:
        """Analyze a message and create an alert for medium/high-risk results."""
        event = self._security.analyze_message(message)
        alert = None
        if event["risk_level"] in {"medium", "high"}:
            alert = self._security.create_security_alert(event_id=event["id"], severity=event["risk_level"])
        result = {"event": event, "alert": alert}
        if self._conversation_model:
            result["guidance"] = self._conversation_model.respond(
                instruction="You are Guardian Agent. Give brief, cautious safety guidance. Never ask for or repeat sensitive data.",
                user_message=message,
                specialist_context=str(result),
            )
        return result

    def medication_supply(self) -> list[dict[str, Any]]:
        """Calculate remaining medication days using schedule times and Inventory MCP stock."""
        results: list[dict[str, Any]] = []
        inventory = {item["schedule_id"]: item for item in self._inventory.check_inventory() if item.get("schedule_id")}
        for schedule in self._health.get_medication_schedule():
            item = inventory.get(schedule["id"])
            daily_units = len(schedule["daily_times"])  # TODO: Use explicit per-dose quantities when Health MCP adds them.
            units_available = item["units_available"] if item else 0
            days_remaining = units_available // daily_units if daily_units else 0
            results.append({
                "medication_name": schedule["medication_name"],
                "units_available": units_available,
                "daily_units": daily_units,
                "days_remaining": days_remaining,
                "refill_warning": days_remaining <= 7,
                "message": "Seven days or fewer of medicine remain; ask the user before ordering." if days_remaining <= 7 else None,
            })
        return results

    def phone_messages(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """Read stored simulated phone messages without creating an event or alert."""
        return self._security.get_phone_messages(limit=limit)

    def request_medication_replenishment(self, *, medication_name: str, quantity: int, user_confirmed: bool) -> dict[str, Any]:
        """Create a replenishment request only after explicit confirmation."""
        request = self._inventory.request_purchase(
            medication_name=medication_name, quantity=quantity, user_confirmed=user_confirmed,
        )
        return request
