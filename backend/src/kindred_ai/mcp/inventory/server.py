"""Inventory MCP transport boundary; its data store is isolated to this domain."""

from datetime import date, datetime
from typing import Any

from fastmcp import FastMCP

from kindred_ai.application.inventory.service import get_inventory_service

mcp = FastMCP("Inventory MCP")


@mcp.tool()
async def check_inventory() -> list[dict[str, Any]]:
    """Get medication inventory for the prototype user."""
    return [item.to_dict() for item in get_inventory_service().check_inventory()]


@mcp.tool()
async def upsert_medication_inventory(
    schedule_id: str,
    medication_name: str,
    units_available: int,
    last_purchased_on: date,
) -> dict[str, Any]:
    """Create or update local medicine stock linked to a Health schedule."""
    return get_inventory_service().upsert_medication_inventory(
        schedule_id=schedule_id,
        medication_name=medication_name,
        units_available=units_available,
        last_purchased_on=last_purchased_on,
    ).to_dict()


@mcp.tool()
async def request_purchase(medication_name: str, quantity: int, user_confirmed: bool) -> dict[str, Any]:
    """Create a confirmed medication replenishment request."""
    return get_inventory_service().request_purchase(
        medication_name=medication_name, quantity=quantity, user_confirmed=user_confirmed,
    ).to_dict()

@mcp.tool()
async def check_household_inventory() -> list[dict[str, Any]]:
    """Get Logistics-owned household stock and its reorder signals."""
    return [item.to_dict() for item in get_inventory_service().check_household_inventory()]


@mcp.tool()
async def request_household_purchase(item_name: str, quantity: int, user_confirmed: bool) -> dict[str, Any]:
    """Record a user-confirmed household purchase request; no external order is placed."""
    return get_inventory_service().request_household_purchase(
        item_name=item_name, quantity=quantity, user_confirmed=user_confirmed,
    ).to_dict()


@mcp.tool()
async def create_reminder(title: str, remind_at: datetime) -> dict[str, str]:
    """Schedule a local household reminder. Notification delivery is not implemented yet."""
    return get_inventory_service().create_reminder(title=title, remind_at=remind_at).to_dict()


@mcp.tool()
async def get_reminders() -> list[dict[str, str]]:
    """Get scheduled local reminders, ordered by the next due reminder."""
    return [reminder.to_dict() for reminder in get_inventory_service().get_reminders()]
