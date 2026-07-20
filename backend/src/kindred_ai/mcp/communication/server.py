"""Communication MCP transport boundary; its data store is isolated to this domain."""

from fastmcp import FastMCP
from kindred_ai.application.communication.service import get_communication_service

mcp = FastMCP("Communication MCP")


@mcp.tool()
async def send_family_message(contact_id: str, content: str, user_approved: bool) -> dict:
    """Queue an explicitly approved family message; no external delivery occurs."""
    return get_communication_service().send_family_message(contact_id, content, user_approved)

@mcp.tool()
async def get_family_contacts() -> list[dict]:
    return get_communication_service().list_contacts()


@mcp.tool()
async def get_phone_book() -> list[dict]:
    """List approved family contacts the prototype user may ask to call."""
    return get_communication_service().list_phone_book()


@mcp.tool()
async def add_phone_book_contact(
    display_name: str,
    relationship: str,
    phone_number: str,
    approved_for_calls: bool = True,
) -> dict:
    """Add a family phone-book contact for simulated communication only."""
    return get_communication_service().add_phone_book_contact(
        display_name, relationship, phone_number, approved_for_calls,
    )


@mcp.tool()
async def request_family_call(contact_query: str) -> dict:
    """Record a requested call; this prototype never starts a real phone call."""
    return get_communication_service().request_family_call(contact_query)


@mcp.tool()
async def create_notification() -> None:
    """Create an authorized notification."""
    # TODO: Define notification policy, routing, and delivery status handling.
    raise NotImplementedError
