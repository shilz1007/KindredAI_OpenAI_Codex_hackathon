"""Runtime-safe configuration packaged with Kindred AI."""

from .agent_registry import AgentDefinition, AgentRegistry, get_agent_registry

__all__ = ["AgentDefinition", "AgentRegistry", "get_agent_registry"]
