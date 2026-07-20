"""Guardian Agent orchestration over approved Health, Security, and Inventory services."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from kindred_ai.application.ports.conversation_model import ConversationModel
from kindred_ai.infrastructure.mcp_clients import HealthMcpClient, InventoryMcpClient, SecurityMcpClient


class GuardianAgent:
    """Coordinates prototype safety and medication-replenishment workflows."""

    def __init__(self, security: SecurityMcpClient, health: HealthMcpClient, inventory: InventoryMcpClient, conversation_model: ConversationModel | None = None, instruction: str = "") -> None:
        self._security = security
        self._health = health
        self._inventory = inventory
        self._conversation_model = conversation_model
        self._instruction = instruction

    def analyze_message(self, message: str) -> dict[str, Any]:
        """Analyze a message and create an alert for medium/high-risk results."""
        event = self._security.analyze_message(message)
        alert = None
        if event["risk_level"] in {"medium", "high"}:
            alert = self._security.create_security_alert(event_id=event["id"], severity=event["risk_level"])
        result = {"event": event, "alert": alert}
        if self._conversation_model:
            result["guidance"] = self._conversation_model.respond(
                instruction=self._instruction + "\n\nGive brief, cautious safety guidance. Never ask for or repeat sensitive data.",
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

    def medication_schedule(self) -> list[dict[str, Any]]:
        """Read active schedules for the daily briefing; no write is performed."""
        return self._health.get_medication_schedule()

    def medication_status_today(self) -> dict[str, list[dict[str, str]]]:
        """Compare today's schedule with persisted taken-dose records through Health MCP."""
        now = datetime.now(ZoneInfo("Europe/Oslo")).strftime("%H:%M")
        explicitly_missed = {
            (str(record["schedule_id"]), str(record["scheduled_time"]))
            for record in self._health.get_missed_medication_doses_today()
        }
        taken_by_schedule: dict[str, int] = {}
        for record in self._health.get_medication_status_today():
            schedule_id = str(record["schedule_id"])
            taken_by_schedule[schedule_id] = taken_by_schedule.get(schedule_id, 0) + 1
        missed: list[dict[str, str]] = []
        upcoming: list[dict[str, str]] = []
        for schedule in self._health.get_medication_schedule():
            taken_count = taken_by_schedule.get(schedule["id"], 0)
            for index, scheduled_time in enumerate(schedule["daily_times"]):
                dose = {"medication_name": schedule["medication_name"], "scheduled_time": scheduled_time}
                if (schedule["id"], scheduled_time) in explicitly_missed:
                    missed.append(dose)
                    continue
                if index < taken_count:
                    continue
                if scheduled_time <= now:
                    missed.append(dose)
                else:
                    upcoming.append(dose)
        missed.sort(key=lambda dose: (dose["scheduled_time"], dose["medication_name"]))
        upcoming.sort(key=lambda dose: (dose["scheduled_time"], dose["medication_name"]))
        return {"not_taken": missed, "upcoming": upcoming}

    def record_medication_missed(self, medication_name: str, scheduled_time: str) -> dict[str, Any]:
        """Persist an explicit missed-dose report for one named scheduled medicine."""
        matches = [
            schedule for schedule in self._health.get_medication_schedule()
            if schedule["medication_name"].casefold() == medication_name.casefold()
        ]
        if not matches:
            raise ValueError(f"I could not find an active medicine called {medication_name}.")
        return self._health.record_medication_missed(matches[0]["id"], scheduled_time)

    def record_medication_taken(self, medication_name: str | None) -> dict[str, Any]:
        """Record a user-confirmed named dose, then return its current supply status."""
        schedules = self._health.get_medication_schedule()
        if not medication_name:
            return {
                "status": "needs_clarification",
                "message": "Please tell me which medicine you have taken.",
            }
        matches = [schedule for schedule in schedules if schedule["medication_name"].casefold() == medication_name.casefold()]
        if not matches:
            return {
                "status": "needs_clarification",
                "message": f"I could not find an active medicine called {medication_name}.",
            }
        schedule = matches[0]
        record = self._health.record_medication_taken(schedule["id"])
        supply = next((item for item in self.medication_supply() if item["medication_name"].casefold() == schedule["medication_name"].casefold()), None)
        return {
            "status": "recorded",
            "medication_name": schedule["medication_name"],
            "record": record,
            "supply": supply,
        }

    def phone_messages(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """Read stored simulated phone messages without creating an event or alert."""
        return self._security.get_phone_messages(limit=limit)

    def request_medication_replenishment(self, *, medication_name: str, quantity: int, user_confirmed: bool) -> dict[str, Any]:
        """Create a replenishment request only after explicit confirmation."""
        request = self._inventory.request_purchase(
            medication_name=medication_name, quantity=quantity, user_confirmed=user_confirmed,
        )
        return request
