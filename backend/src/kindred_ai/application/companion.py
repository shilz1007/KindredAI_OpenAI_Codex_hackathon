from functools import lru_cache
from kindred_ai.agents.companion import CompanionAgent
from kindred_ai.config.model_settings import get_model_settings
from kindred_ai.infrastructure.mcp_clients import MemoryMcpClient, CommunicationMcpClient
from kindred_ai.infrastructure.openai import OpenAIConversationModel

@lru_cache(maxsize=1)
def get_companion_agent():
    settings=get_model_settings()
    return CompanionAgent(MemoryMcpClient(), CommunicationMcpClient(), OpenAIConversationModel(api_key=settings.api_key, model=settings.agents_model))
