"""Swagger-visible HTTP adapter for Health MCP use cases."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from kindred_ai.application.health.service import get_health_service

router = APIRouter(prefix="/health", tags=["Health MCP"])


class MedicationTakenRequest(BaseModel):
    """Input accepted when recording a taken medication dose."""

    schedule_id: str = Field(examples=["demo-schedule-metformin"])
    taken_at: datetime | None = Field(default=None, examples=["2026-07-18T08:00:00+02:00"])
    note: str | None = Field(default=None, examples=["Taken after breakfast"])


@router.get("/medication-schedule")
def get_medication_schedule() -> list[dict[str, object]]:
    """Get active medication schedules for the internal demo user."""
    return [schedule.to_dict() for schedule in get_health_service().get_medication_schedule()]


@router.post("/medication-taken", status_code=status.HTTP_201_CREATED)
def record_medication_taken(payload: MedicationTakenRequest) -> dict[str, str | None]:
    """Record a dose reported as taken."""
    try:
        record = get_health_service().record_medication_taken(
            schedule_id=payload.schedule_id,
            taken_at=payload.taken_at,
            note=payload.note,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return record.to_dict()


@router.get("/events")
def get_health_events() -> list[dict[str, str | None]]:
    """Get health events for the internal demo user."""
    return [event.to_dict() for event in get_health_service().get_health_events()]
