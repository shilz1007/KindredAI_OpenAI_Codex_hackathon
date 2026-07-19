"""Inventory MCP application use cases."""

from .service import InventoryService, get_inventory_service, initialize_inventory_service

__all__ = ["InventoryService", "get_inventory_service", "initialize_inventory_service"]
