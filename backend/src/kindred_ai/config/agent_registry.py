"""Startup-validated YAML catalog for agent metadata and allowed MCP access."""

import os
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

AgentId = Literal["master", "router", "companion", "guardian", "logistics", "research"]

APPROVED_AGENT_MCP_SERVERS: dict[str, frozenset[str]] = {
    "master": frozenset(),
    "router": frozenset(),
    "companion": frozenset({"memory", "communication"}),
    "guardian": frozenset({"security", "health", "inventory"}),
    "logistics": frozenset({"inventory"}),
    "research": frozenset({"tavily"}),
}
KNOWN_MCP_SERVERS = frozenset().union(*APPROVED_AGENT_MCP_SERVERS.values())


class AgentCatalogConfigurationError(ValueError):
    """Raised when the agent catalog is unsafe or inconsistent with architecture."""


class AgentDefinition(BaseModel):
    """Declarative metadata for one agent; executable behavior stays in Python."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: AgentId
    display_name: str
    purpose: str
    capabilities: list[str]
    allowed_mcp_servers: list[str]
    instruction: str


class AgentCatalog(BaseModel):
    """Versioned schema for the entire agent catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    catalog_version: Literal[1]
    agents: list[AgentDefinition]

    @model_validator(mode="after")
    def validate_agent_ids(self) -> "AgentCatalog":
        ids = [agent.id for agent in self.agents]
        if len(ids) != len(set(ids)):
            raise ValueError("Agent catalog contains duplicate agent IDs.")
        if set(ids) != set(APPROVED_AGENT_MCP_SERVERS):
            raise ValueError("Agent catalog must define master, router, companion, guardian, logistics, and research exactly once.")
        return self


class AgentRegistry:
    """Read-only runtime view of validated agent definitions."""

    def __init__(self, catalog: AgentCatalog) -> None:
        self._agents = {agent.id: agent for agent in catalog.agents}
        self._validate_mcp_ownership()

    @classmethod
    def from_yaml_text(cls, content: str) -> "AgentRegistry":
        """Parse and validate catalog text without executing configuration content."""
        try:
            raw_catalog = yaml.safe_load(content)
            catalog = AgentCatalog.model_validate(raw_catalog)
        except (yaml.YAMLError, ValidationError, TypeError) as error:
            raise AgentCatalogConfigurationError(f"Invalid agent catalog: {error}") from error
        try:
            return cls(catalog)
        except ValueError as error:
            raise AgentCatalogConfigurationError(f"Invalid agent catalog: {error}") from error

    @classmethod
    def from_path(cls, catalog_path: Path) -> "AgentRegistry":
        """Load a catalog from a deployment-provided path."""
        try:
            return cls.from_yaml_text(catalog_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise AgentCatalogConfigurationError(f"Cannot read agent catalog at {catalog_path}: {error}") from error

    @classmethod
    def load_default(cls) -> "AgentRegistry":
        """Load the packaged catalog or an explicit deployment override."""
        configured_path = os.getenv("KINDRED_AGENT_CATALOG_PATH")
        if configured_path:
            return cls.from_path(Path(configured_path))
        catalog_file = resources.files("kindred_ai.config").joinpath("agents.yaml")
        return cls.from_yaml_text(catalog_file.read_text(encoding="utf-8"))

    def _validate_mcp_ownership(self) -> None:
        for agent_id, expected_mcp_servers in APPROVED_AGENT_MCP_SERVERS.items():
            actual_mcp_servers = frozenset(self._agents[agent_id].allowed_mcp_servers)
            unknown_mcp_servers = actual_mcp_servers - KNOWN_MCP_SERVERS
            if unknown_mcp_servers:
                unknown = ", ".join(sorted(unknown_mcp_servers))
                raise ValueError(f"Agent '{agent_id}' has unknown MCP servers: {unknown}.")
            if actual_mcp_servers != expected_mcp_servers:
                expected = ", ".join(sorted(expected_mcp_servers)) or "none"
                actual = ", ".join(sorted(actual_mcp_servers)) or "none"
                raise ValueError(
                    f"Agent '{agent_id}' MCP servers must be [{expected}], but found [{actual}]."
                )

    def get(self, agent_id: AgentId) -> AgentDefinition:
        """Return one validated agent definition."""
        return self._agents[agent_id]

    def all(self) -> tuple[AgentDefinition, ...]:
        """Return agent definitions in the catalog's declared order."""
        return tuple(self._agents[agent_id] for agent_id in APPROVED_AGENT_MCP_SERVERS)


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    """Load the validated catalog once during the process lifetime."""
    return AgentRegistry.load_default()


def initialize_agent_registry() -> None:
    """Fail FastAPI startup early when agent configuration is invalid."""
    get_agent_registry()
