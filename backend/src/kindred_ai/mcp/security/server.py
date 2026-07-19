"""Security MCP transport boundary; its data store is isolated to this domain."""

from typing import Any

from fastmcp import FastMCP

from kindred_ai.application.security.service import get_security_service

mcp = FastMCP("Security MCP")


@mcp.tool()
async def analyze_message(message: str) -> dict[str, Any]:
    """Analyze and record a message using the MVP's deterministic safety rules."""
    return get_security_service().analyze_message(message).to_dict()


@mcp.tool()
async def create_security_alert(event_id: str, severity: str = "medium") -> dict[str, Any]:
    """Create an alert for an existing security event."""
    return get_security_service().create_security_alert(event_id=event_id, severity=severity).to_dict()


@mcp.tool()
async def get_security_events(limit: int = 20) -> list[dict[str, Any]]:
    """Get recorded security events, newest first."""
    return [event.to_dict() for event in get_security_service().get_security_events(limit=limit)]


@mcp.tool()
async def get_phone_messages(limit: int = 20) -> list[dict[str, Any]]:
    """Get simulated phone messages stored by Security MCP, newest first."""
    return [message.to_dict() for message in get_security_service().get_phone_messages(limit=limit)]
