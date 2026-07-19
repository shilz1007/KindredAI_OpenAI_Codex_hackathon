"""Pure domain models for the Health MCP database."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MedicationSchedule:
    """An active or inactive medication plan for one health-domain user."""

    id: str
    medication_name: str
    dose_instructions: str
    timezone: str
    daily_times: tuple[str, ...]
    is_active: bool

    def to_dict(self) -> dict[str, object]:
        """Return a transport-safe representation."""
        return {
            "id": self.id,
            "medication_name": self.medication_name,
            "dose_instructions": self.dose_instructions,
            "timezone": self.timezone,
            "daily_times": list(self.daily_times),
            "is_active": self.is_active,
        }


@dataclass(frozen=True, slots=True)
class MedicationTakenRecord:
    """An auditable record of a medication dose reported as taken."""

    id: str
    schedule_id: str
    taken_at: datetime
    note: str | None

    def to_dict(self) -> dict[str, str | None]:
        """Return a transport-safe representation."""
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "taken_at": self.taken_at.isoformat(),
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class HealthEvent:
    """A generic health-domain event."""

    id: str
    event_type: str
    occurred_at: datetime
    details: str | None
    severity: str

    def to_dict(self) -> dict[str, str | None]:
        """Return a transport-safe representation."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "details": self.details,
            "severity": self.severity,
        }
