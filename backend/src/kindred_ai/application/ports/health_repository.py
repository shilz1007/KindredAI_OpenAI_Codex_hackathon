"""Application port for the isolated Health MCP persistence store."""

from datetime import datetime
from typing import Protocol

from kindred_ai.domain.health import HealthEvent, MedicationSchedule, MedicationTakenRecord


class HealthRepository(Protocol):
    """Persistence operations required by Health MCP use cases."""

    def get_active_medication_schedules(self, user_id: str) -> list[MedicationSchedule]: ...

    def get_active_schedule(self, user_id: str, schedule_id: str) -> MedicationSchedule | None: ...

    def add_medication_schedule(
        self,
        *,
        schedule_id: str,
        user_id: str,
        medication_name: str,
        dose_instructions: str,
        timezone: str,
        daily_times: tuple[str, ...],
    ) -> MedicationSchedule: ...

    def add_medication_taken_record(
        self,
        *,
        record_id: str,
        user_id: str,
        schedule_id: str,
        taken_at: datetime,
        note: str | None,
    ) -> MedicationTakenRecord: ...

    def get_health_events(self, user_id: str) -> list[HealthEvent]: ...
