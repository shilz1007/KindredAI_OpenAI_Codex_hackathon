"""Factory for the internal Router Agent."""

from functools import lru_cache

from kindred_ai.agents.router import RouterAgent
from kindred_ai.config.agent_registry import get_agent_registry
from kindred_ai.config.model_settings import get_model_settings
from kindred_ai.infrastructure.openai.agent_router import OpenAIAgentRouter


@lru_cache(maxsize=1)
def get_router_agent() -> RouterAgent:
    """Create the no-MCP Router Agent from its validated YAML definition."""
    definition = get_agent_registry().get("router")
    if definition.allowed_mcp_servers:
        raise RuntimeError("Router Agent must not have direct MCP access.")
    settings = get_model_settings()
    return RouterAgent(
        OpenAIAgentRouter(
            api_key=settings.api_key,
            model=settings.agents_model,
            instruction=definition.instruction,
        )
    )
