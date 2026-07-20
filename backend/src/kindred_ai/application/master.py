"""Factory for the Master Agent's model and approved specialist dependencies."""

from functools import lru_cache

from kindred_ai.agents.master import MasterAgent
from kindred_ai.application.guardian import get_guardian_agent
from kindred_ai.application.logistics import get_logistics_agent
from kindred_ai.application.research import get_research_agent
from kindred_ai.application.companion import get_companion_agent
from kindred_ai.config.agent_registry import get_agent_registry
from kindred_ai.config.model_settings import get_model_settings
from kindred_ai.infrastructure.openai import OpenAIConversationModel
from kindred_ai.infrastructure.openai.speech import OpenAISpeechService


@lru_cache(maxsize=1)
def get_master_agent() -> MasterAgent:
    """Create Master from its configured model and specialist-agent access."""
    definition = get_agent_registry().get("master")
    if definition.allowed_mcp_servers:
        raise RuntimeError("Master Agent must not have direct MCP access.")
    settings = get_model_settings()
    # The React Care Hub text workflow uses the Responses API. The Master
    # model setting is reserved for the Realtime WebSocket voice adapter;
    # specialist-model configuration is the supported text fallback.
    model = OpenAIConversationModel(api_key=settings.api_key, model=settings.agents_model)
    # Import lazily to avoid an agent-package import cycle while retaining a
    # separate Router Agent factory boundary.
    from kindred_ai.application.router import get_router_agent
    return MasterAgent(
        model,
        get_guardian_agent(),
        get_router_agent(),
        get_companion_agent(),
        get_logistics_agent(),
        get_research_agent(),
        instruction=definition.instruction,
    )


@lru_cache(maxsize=1)
def get_master_speech_service() -> OpenAISpeechService:
    """Create the single voice used by the browser Care Hub."""
    settings = get_model_settings()
    return OpenAISpeechService(
        api_key=settings.api_key,
        model=settings.speech_model,
        voice=settings.speech_voice,
    )
