"""Tests for the startup-validated agent YAML catalog."""

import os
import tempfile
import unittest
from pathlib import Path

from kindred_ai.config.agent_registry import (
    APPROVED_AGENT_MCP_SERVERS,
    AgentCatalogConfigurationError,
    AgentRegistry,
    get_agent_registry,
)
from kindred_ai.presentation.api.app import create_app


class AgentRegistryTests(unittest.TestCase):
    def tearDown(self) -> None:
        get_agent_registry.cache_clear()
        os.environ.pop("KINDRED_AGENT_CATALOG_PATH", None)

    def test_default_catalog_defines_all_agents_with_approved_mcp_access(self) -> None:
        registry = AgentRegistry.load_default()
        self.assertEqual(set(APPROVED_AGENT_MCP_SERVERS), {agent.id for agent in registry.all()})
        for agent_id, expected_servers in APPROVED_AGENT_MCP_SERVERS.items():
            self.assertEqual(expected_servers, frozenset(registry.get(agent_id).allowed_mcp_servers))

    def test_duplicate_agent_ids_fail_validation(self) -> None:
        duplicate_catalog = """
catalog_version: 1
agents:
  - id: master
    display_name: Master
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: []
    instruction: Test
  - id: research
    display_name: Research
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: [tavily]
    instruction: Test
  - id: router
    display_name: Router
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: []
    instruction: Test
  - id: master
    display_name: Master duplicate
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: []
    instruction: Test
"""
        with self.assertRaisesRegex(AgentCatalogConfigurationError, "duplicate agent IDs"):
            AgentRegistry.from_yaml_text(duplicate_catalog)

    def test_unknown_mcp_and_invalid_ownership_fail_validation(self) -> None:
        unknown_mcp_catalog = """
catalog_version: 1
agents:
  - id: master
    display_name: Master
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: [unrecognized]
    instruction: Test
  - id: research
    display_name: Research
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: [tavily]
    instruction: Test
  - id: router
    display_name: Router
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: []
    instruction: Test
  - id: companion
    display_name: Companion
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: [memory, communication]
    instruction: Test
  - id: guardian
    display_name: Guardian
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: [security, health, inventory]
    instruction: Test
  - id: logistics
    display_name: Logistics
    purpose: Test
    capabilities: [Test]
    allowed_mcp_servers: [inventory]
    instruction: Test
"""
        with self.assertRaisesRegex(AgentCatalogConfigurationError, "unknown MCP servers: unrecognized"):
            AgentRegistry.from_yaml_text(unknown_mcp_catalog)
        invalid_ownership_catalog = unknown_mcp_catalog.replace("[unrecognized]", "[memory]")
        with self.assertRaisesRegex(AgentCatalogConfigurationError, r"must be \[none\]"):
            AgentRegistry.from_yaml_text(invalid_ownership_catalog)

    def test_fastapi_startup_initializes_catalog_override(self) -> None:
        catalog_text = (Path(__file__).parents[1] / "src" / "kindred_ai" / "config" / "agents.yaml").read_text(encoding="utf-8")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as file:
            file.write(catalog_text)
            catalog_path = file.name
        try:
            os.environ["KINDRED_AGENT_CATALOG_PATH"] = catalog_path
            get_agent_registry.cache_clear()
            application = create_app()
            self.assertEqual("Kindred AI Backend", application.title)
            self.assertEqual("Guardian Agent", get_agent_registry().get("guardian").display_name)
            self.assertEqual("Router Agent", get_agent_registry().get("router").display_name)
            self.assertEqual("Research Agent", get_agent_registry().get("research").display_name)
        finally:
            Path(catalog_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
