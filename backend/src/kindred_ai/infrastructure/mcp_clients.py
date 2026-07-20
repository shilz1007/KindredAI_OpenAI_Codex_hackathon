"""FastMCP client adapters used by agents instead of direct MCP service imports."""

import asyncio
import os
from typing import Any

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from kindred_ai.infrastructure.observability import observation, record_output


def _call(server: FastMCP, url_variable: str, tool: str, arguments: dict[str, Any]) -> Any:
    """Call a tool via FastMCP; an HTTP URL selects a standalone MCP server."""
    transport: FastMCP | str = os.getenv(url_variable) or server

    async def invoke() -> Any:
        async with Client(transport) as client:
            result = await client.call_tool(tool, arguments)
            if result.is_error:
                raise RuntimeError(f"MCP tool '{tool}' failed: {result.content}")
            content = result.structured_content
            # FastMCP wraps top-level list tool results under a `result` key.
            return content["result"] if isinstance(content, dict) and set(content) == {"result"} else content

    with observation(f"mcp.{tool}", as_type="tool", input={"tool": tool, "arguments": arguments}, metadata={"mcp_url_variable": url_variable}) as tool_observation:
        try:
            output = asyncio.run(invoke())
            record_output(tool_observation, output)
            return output
        except ToolError as error:
            raise ValueError(str(error)) from error


class SecurityMcpClient:
    def analyze_message(self, message: str) -> dict[str, Any]:
        from kindred_ai.mcp.security.server import mcp
        return _call(mcp, "KINDRED_MCP_SECURITY_URL", "analyze_message", {"message": message})

    def create_security_alert(self, event_id: str, severity: str) -> dict[str, Any]:
        from kindred_ai.mcp.security.server import mcp
        return _call(mcp, "KINDRED_MCP_SECURITY_URL", "create_security_alert", {"event_id": event_id, "severity": severity})

    def get_phone_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        from kindred_ai.mcp.security.server import mcp
        return _call(mcp, "KINDRED_MCP_SECURITY_URL", "get_phone_messages", {"limit": limit})


class HealthMcpClient:
    def get_medication_schedule(self) -> list[dict[str, Any]]:
        from kindred_ai.mcp.health.server import mcp
        return _call(mcp, "KINDRED_MCP_HEALTH_URL", "get_medication_schedule", {})


class InventoryMcpClient:
    def check_inventory(self) -> list[dict[str, Any]]:
        from kindred_ai.mcp.inventory.server import mcp
        return _call(mcp, "KINDRED_MCP_INVENTORY_URL", "check_inventory", {})

    def request_purchase(self, medication_name: str, quantity: int, user_confirmed: bool) -> dict[str, Any]:
        from kindred_ai.mcp.inventory.server import mcp
        return _call(mcp, "KINDRED_MCP_INVENTORY_URL", "request_purchase", {"medication_name": medication_name, "quantity": quantity, "user_confirmed": user_confirmed})

    def check_household_inventory(self) -> list[dict[str, Any]]:
        from kindred_ai.mcp.inventory.server import mcp
        return _call(mcp, "KINDRED_MCP_INVENTORY_URL", "check_household_inventory", {})

    def request_household_purchase(self, item_name: str, quantity: int, user_confirmed: bool) -> dict[str, Any]:
        from kindred_ai.mcp.inventory.server import mcp
        return _call(mcp, "KINDRED_MCP_INVENTORY_URL", "request_household_purchase", {"item_name": item_name, "quantity": quantity, "user_confirmed": user_confirmed})

    def create_reminder(self, title: str, remind_at: str) -> dict[str, Any]:
        from kindred_ai.mcp.inventory.server import mcp
        return _call(mcp, "KINDRED_MCP_INVENTORY_URL", "create_reminder", {"title": title, "remind_at": remind_at})

    def get_reminders(self) -> list[dict[str, Any]]:
        from kindred_ai.mcp.inventory.server import mcp
        return _call(mcp, "KINDRED_MCP_INVENTORY_URL", "get_reminders", {})

class MemoryMcpClient:
    def get_user_profile(self):
        from kindred_ai.mcp.memory.server import mcp
        return _call(mcp, "KINDRED_MCP_MEMORY_URL", "get_user_profile", {})
    def retrieve_history(self, limit: int = 5):
        from kindred_ai.mcp.memory.server import mcp
        return _call(mcp, "KINDRED_MCP_MEMORY_URL", "retrieve_history", {"limit": limit})

class CommunicationMcpClient:
    def get_family_contacts(self):
        from kindred_ai.mcp.communication.server import mcp
        return _call(mcp, "KINDRED_MCP_COMMUNICATION_URL", "get_family_contacts", {})
    def send_family_message(self, contact_id: str, content: str, user_approved: bool):
        from kindred_ai.mcp.communication.server import mcp
        return _call(mcp, "KINDRED_MCP_COMMUNICATION_URL", "send_family_message", {"contact_id":contact_id,"content":content,"user_approved":user_approved})
    def get_phone_book(self):
        from kindred_ai.mcp.communication.server import mcp
        return _call(mcp, "KINDRED_MCP_COMMUNICATION_URL", "get_phone_book", {})
    def add_phone_book_contact(self, display_name: str, relationship: str, phone_number: str, approved_for_calls: bool = True):
        from kindred_ai.mcp.communication.server import mcp
        return _call(mcp, "KINDRED_MCP_COMMUNICATION_URL", "add_phone_book_contact", {"display_name": display_name, "relationship": relationship, "phone_number": phone_number, "approved_for_calls": approved_for_calls})
    def request_family_call(self, contact_query: str):
        from kindred_ai.mcp.communication.server import mcp
        return _call(mcp, "KINDRED_MCP_COMMUNICATION_URL", "request_family_call", {"contact_query": contact_query})
