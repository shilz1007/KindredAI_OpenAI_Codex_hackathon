"""Factory for the catalog-authorized Tavily Research Agent."""

import os
from functools import lru_cache

from dotenv import load_dotenv

from kindred_ai.agents.research import ResearchAgent
from kindred_ai.config.agent_registry import get_agent_registry
from kindred_ai.config.model_settings import ENVIRONMENT_FILE, get_model_settings
from kindred_ai.infrastructure.openai import TavilyResearchModel, UnavailableResearchModel
from kindred_ai.infrastructure.research import SqliteResearchHistoryRepository


@lru_cache(maxsize=1)
def get_research_agent() -> ResearchAgent:
    """Build Research only when its catalog permission is exactly Tavily."""
    definition = get_agent_registry().get("research")
    if frozenset(definition.allowed_mcp_servers) != frozenset({"tavily"}):
        raise RuntimeError("Research Agent is not configured with Tavily-only MCP access.")
    load_dotenv(ENVIRONMENT_FILE)
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    history = SqliteResearchHistoryRepository.from_environment()
    history.initialize()
    settings = get_model_settings()
    model = (
        TavilyResearchModel(api_key=settings.api_key, tavily_api_key=tavily_api_key, model=settings.agents_model)
        if tavily_api_key
        else UnavailableResearchModel()
    )
    return ResearchAgent(
        model,
        history,
        definition.instruction,
    )


def initialize_research_service() -> None:
    """Initialize the isolated local history database at application startup."""
    SqliteResearchHistoryRepository.from_environment().initialize()
