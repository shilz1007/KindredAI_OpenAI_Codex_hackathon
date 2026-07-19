"""Factory for the Master Agent's model and approved specialist dependencies."""

from functools import lru_cache

from kindred_ai.agents.master import MasterAgent
from kindred_ai.application.guardian import get_guardian_agent
from kindred_ai.application.logistics import get_logistics_agent
from kindred_ai.application.companion import get_companion_agent
from kindred_ai.infrastructure.openai.agent_router import OpenAIAgentRouter
from kindred_ai.config.agent_registry import get_agent_registry
from kindred_ai.config.model_settings import get_model_settings
from kindred_ai.infrastructure.openai import OpenAIConversationModel


@lru_cache(maxsize=1)
def get_master_agent() -> MasterAgent:
    """Create Master from its configured model and specialist-agent access."""
    if get_agent_registry().get("master").allowed_mcp_servers:
        raise RuntimeError("Master Agent must not have direct MCP access.")
    settings = get_model_settings()
    # The temporary Gradio text harness uses the Responses API. The Master
    # model setting is reserved for the Realtime WebSocket voice adapter;
    # specialist-model configuration is the supported text fallback.
    model = OpenAIConversationModel(api_key=settings.api_key, model=settings.agents_model)
    router = OpenAIAgentRouter(api_key=settings.api_key, model=settings.agents_model)
    return MasterAgent(model, get_guardian_agent(), router, get_companion_agent(), get_logistics_agent())
