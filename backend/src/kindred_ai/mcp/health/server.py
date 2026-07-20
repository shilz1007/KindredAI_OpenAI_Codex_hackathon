"""Health MCP transport boundary; its data store is isolated to this domain."""

from datetime import datetime
from typing import Any

from fastmcp import FastMCP

from kindred_ai.application.health.service import get_health_service

mcp = FastMCP("Health MCP")


@mcp.tool()
async def get_medication_schedule() -> list[dict[str, Any]]:
    """Get the active medication schedules for the demo user."""
    return [schedule.to_dict() for schedule in get_health_service().get_medication_schedule()]


@mcp.tool()
async def create_medication_schedule(
    medication_name: str,
    dose_instructions: str,
    daily_times: list[str],
    timezone: str = "Europe/Oslo",
) -> dict[str, Any]:
    """Create an active medication plan for the prototype demo user."""
    return get_health_service().create_medication_schedule(
        medication_name=medication_name,
        dose_instructions=dose_instructions,
        daily_times=daily_times,
        timezone=timezone,
    ).to_dict()


@mcp.tool()
async def record_medication_taken(
    schedule_id: str,
    taken_at: datetime | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Record that a dose from an active medication schedule was taken."""
    record = get_health_service().record_medication_taken(
        schedule_id=schedule_id,
        taken_at=taken_at,
        note=note,
    )
    return record.to_dict()


@mcp.tool()
async def get_health_events() -> list[dict[str, Any]]:
    """Get health events for the demo user, newest first."""
    return [event.to_dict() for event in get_health_service().get_health_events()]
