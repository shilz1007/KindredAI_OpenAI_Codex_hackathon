"""Logistics Agent for non-medication household stock and reminders."""

from typing import Any

from kindred_ai.infrastructure.mcp_clients import InventoryMcpClient


class LogisticsAgent:
    """Uses only the household subset of Inventory MCP tools."""

    def __init__(self, inventory_client: InventoryMcpClient) -> None:
        self._inventory = inventory_client

    def household_inventory(self) -> list[dict[str, Any]]:
        return self._inventory.check_household_inventory()

    def request_purchase(self, *, item_name: str, quantity: int, user_confirmed: bool) -> dict[str, Any]:
        """Create a request only after clear user confirmation; never places an external order."""
        return self._inventory.request_household_purchase(item_name, quantity, user_confirmed)

    def schedule_reminder(self, *, title: str, remind_at: str) -> dict[str, Any]:
        """Create a local reminder. TODO: hand due reminders to Communication MCP."""
        return self._inventory.create_reminder(title, remind_at)
