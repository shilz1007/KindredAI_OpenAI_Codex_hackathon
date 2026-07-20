"""Memory MCP transport boundary; its data store is isolated to this domain."""

from typing import Any

from fastmcp import FastMCP

from kindred_ai.application.memory.service import get_memory_service

mcp = FastMCP("Memory MCP")


@mcp.tool()
async def get_user_profile() -> dict[str, Any]:
    """Retrieve the profile of the internal demo user."""
    return get_memory_service().get_user_profile().to_dict()


@mcp.tool()
async def save_memory(
    content: str,
    category: str = "general",
    source: str = "conversation",
    importance: int = 1,
) -> dict[str, Any]:
    """Store an approved memory for the internal demo user."""
    memory = get_memory_service().save_memory(
        content=content, category=category, source=source, importance=importance,
    )
    return memory.to_dict()


@mcp.tool()
async def retrieve_history(limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve the most recent demo-user conversation history."""
    return [entry.to_dict() for entry in get_memory_service().retrieve_history(limit=limit)]


@mcp.tool()
async def retrieve_memories(category: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve approved saved facts, optionally limited to one category."""
    return [memory.to_dict() for memory in get_memory_service().retrieve_memories(category=category, limit=limit)]
