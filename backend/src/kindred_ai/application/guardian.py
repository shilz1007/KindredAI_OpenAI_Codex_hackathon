"""Factory for the Guardian Agent's approved dependencies."""

import os

from kindred_ai.agents.guardian import GuardianAgent
from kindred_ai.config.agent_registry import get_agent_registry
from kindred_ai.config.model_settings import get_model_settings
from kindred_ai.infrastructure.mcp_clients import HealthMcpClient, InventoryMcpClient, SecurityMcpClient
from kindred_ai.infrastructure.openai import OpenAIConversationModel


def get_guardian_agent() -> GuardianAgent:
    """Build Guardian only after configuration confirms its permitted MCP servers."""
    allowed = frozenset(get_agent_registry().get("guardian").allowed_mcp_servers)
    required = frozenset({"security", "health", "inventory"})
    if not required.issubset(allowed):
        raise RuntimeError("Guardian Agent is not configured with its required MCP access.")
    conversation_model = None
    if os.getenv("KINDRED_ENABLE_LLM", "true").lower() == "true" and os.getenv("KINDRED_DISABLE_LLM") != "true":
        settings = get_model_settings()
        conversation_model = OpenAIConversationModel(api_key=settings.api_key, model=settings.agents_model)
    return GuardianAgent(
        SecurityMcpClient(), HealthMcpClient(), InventoryMcpClient(),
        conversation_model,
        get_agent_registry().get("guardian").instruction,
    )
