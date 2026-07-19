"""Regression tests for OpenAI structured-output routing schema."""

import unittest

from kindred_ai.infrastructure.openai.agent_router import _strict_route_schema


class AgentRouterSchemaTests(unittest.TestCase):
    def test_strict_schema_requires_every_declared_property(self) -> None:
        schema = _strict_route_schema()
        self.assertEqual(set(schema["properties"]), set(schema["required"]))
        self.assertNotIn("default", schema["properties"]["household_item_name"])


if __name__ == "__main__":
    unittest.main()
