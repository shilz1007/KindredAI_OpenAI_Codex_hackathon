"""Use cases for the Health MCP demo-user MVP."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from functools import lru_cache
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kindred_ai.application.ports.health_repository import HealthRepository
from kindred_ai.domain.health import HealthEvent, MedicationDoseStatusRecord, MedicationSchedule, MedicationTakenRecord
from kindred_ai.infrastructure.health.sqlite_repository import SqliteHealthRepository

DEMO_USER_ID = "demo-user"


class HealthService:
    """Coordinates Health MCP use cases without exposing SQL to transports."""

    def __init__(self, repository: HealthRepository) -> None:
        self._repository = repository

    def get_medication_schedule(self) -> list[MedicationSchedule]:
        """Return active schedules for the MVP's internal demo user."""
        return self._repository.get_active_medication_schedules(DEMO_USER_ID)

    def create_medication_schedule(
        self,
        *,
        medication_name: str,
        dose_instructions: str,
        daily_times: list[str],
        timezone: str = "Europe/Oslo",
    ) -> MedicationSchedule:
        """Create an active medication plan for the prototype's demo user."""
        if not medication_name.strip():
            raise ValueError("Medication name is required.")
        if not dose_instructions.strip():
            raise ValueError("Dose instructions are required.")
        if not daily_times:
            raise ValueError("At least one daily medication time is required.")
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Medication timezone must be a valid IANA timezone, such as Europe/Oslo.") from error
        try:
            normalized_times = tuple(sorted({datetime.strptime(local_time.strip(), "%H:%M").strftime("%H:%M") for local_time in daily_times}))
        except ValueError as error:
            raise ValueError("Medication times must use 24-hour HH:MM format, such as 08:00.") from error
        return self._repository.add_medication_schedule(
            schedule_id=f"schedule-{uuid4()}",
            user_id=DEMO_USER_ID,
            medication_name=medication_name.strip(),
            dose_instructions=dose_instructions.strip(),
            timezone=timezone,
            daily_times=normalized_times,
        )

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

    def get_medication_taken_records_for_today(self) -> list[MedicationTakenRecord]:
        """Read today's records in the demo user's local Oslo day."""
        oslo = ZoneInfo("Europe/Oslo")
        today = datetime.now(oslo).date()
        return [
            record for record in self._repository.get_medication_taken_records(DEMO_USER_ID)
            if record.taken_at.astimezone(oslo).date() == today
        ]

    def record_medication_missed(self, *, schedule_id: str, scheduled_time: str, note: str | None = None) -> MedicationDoseStatusRecord:
        """Persist a user's report that one named scheduled dose was missed."""
        schedule = self._repository.get_active_schedule(DEMO_USER_ID, schedule_id)
        if schedule is None:
            raise ValueError("Unknown or inactive medication schedule.")
        if scheduled_time not in schedule.daily_times:
            raise ValueError("That time is not scheduled for this medication.")
        oslo_now = datetime.now(ZoneInfo("Europe/Oslo"))
        return self._repository.add_medication_dose_status_record(
            record_id=str(uuid4()), user_id=DEMO_USER_ID, schedule_id=schedule_id,
            scheduled_date=oslo_now.date().isoformat(), scheduled_time=scheduled_time,
            status="missed", recorded_at=oslo_now, note=note,
        )

    def get_medication_dose_status_records_for_today(self) -> list[MedicationDoseStatusRecord]:
        """Read explicitly reported missed doses for the current Oslo day."""
        today = datetime.now(ZoneInfo("Europe/Oslo")).date().isoformat()
        return self._repository.get_medication_dose_status_records(DEMO_USER_ID, today)

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
