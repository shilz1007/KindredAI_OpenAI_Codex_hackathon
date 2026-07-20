from functools import lru_cache
from kindred_ai.agents.companion import CompanionAgent
from kindred_ai.config.agent_registry import get_agent_registry
from kindred_ai.config.model_settings import get_model_settings
from kindred_ai.infrastructure.mcp_clients import MemoryMcpClient, CommunicationMcpClient
from kindred_ai.infrastructure.openai import OpenAIConversationModel

@lru_cache(maxsize=1)
def get_companion_agent():
    settings=get_model_settings()
    definition = get_agent_registry().get("companion")
    if frozenset(definition.allowed_mcp_servers) != frozenset({"memory", "communication"}):
        raise RuntimeError("Companion Agent is not configured with its approved MCP access.")
    return CompanionAgent(MemoryMcpClient(), CommunicationMcpClient(), OpenAIConversationModel(api_key=settings.api_key, model=settings.agents_model), definition.instruction)
