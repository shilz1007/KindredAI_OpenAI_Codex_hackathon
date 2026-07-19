"""Factory for the Logistics Agent's narrowly scoped Inventory MCP access."""

from functools import lru_cache

from kindred_ai.agents.logistics import LogisticsAgent
from kindred_ai.config.agent_registry import get_agent_registry
from kindred_ai.infrastructure.mcp_clients import InventoryMcpClient


@lru_cache(maxsize=1)
def get_logistics_agent() -> LogisticsAgent:
    allowed = frozenset(get_agent_registry().get("logistics").allowed_mcp_servers)
    if allowed != frozenset({"inventory"}):
        raise RuntimeError("Logistics Agent is not configured with its required Inventory MCP access.")
    return LogisticsAgent(InventoryMcpClient())
