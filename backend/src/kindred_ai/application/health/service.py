"""Use cases for the Health MCP demo-user MVP."""

from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

from kindred_ai.application.ports.health_repository import HealthRepository
from kindred_ai.domain.health import HealthEvent, MedicationSchedule, MedicationTakenRecord
from kindred_ai.infrastructure.health.sqlite_repository import SqliteHealthRepository

DEMO_USER_ID = "demo-user"


class HealthService:
    """Coordinates Health MCP use cases without exposing SQL to transports."""

    def __init__(self, repository: HealthRepository) -> None:
        self._repository = repository

    def get_medication_schedule(self) -> list[MedicationSchedule]:
        """Return active schedules for the MVP's internal demo user."""
        return self._repository.get_active_medication_schedules(DEMO_USER_ID)

    def record_medication_taken(
        self,
        *,
        schedule_id: str,
        taken_at: datetime | None,
        note: str | None,
    ) -> MedicationTakenRecord:
        """Persist a taken-dose record after confirming schedule eligibility."""
        if self._repository.get_active_schedule(DEMO_USER_ID, schedule_id) is None:
            raise ValueError("Unknown or inactive medication schedule.")
        timestamp = taken_at or datetime.now(UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return self._repository.add_medication_taken_record(
            record_id=str(uuid4()),
            user_id=DEMO_USER_ID,
            schedule_id=schedule_id,
            taken_at=timestamp,
            note=note,
        )

    def get_health_events(self) -> list[HealthEvent]:
        """Return demo-user health events in descending occurrence order."""
        return self._repository.get_health_events(DEMO_USER_ID)


@lru_cache(maxsize=1)
def get_health_service() -> HealthService:
    """Create and initialize the configured Health MCP service once per process."""
    repository = SqliteHealthRepository.from_environment()
    repository.initialize()
    return HealthService(repository)


def initialize_health_service() -> None:
    """Eagerly initialize Health MCP persistence during application startup."""
    get_health_service()
