"""End-to-end prototype tests for Inventory MCP and Guardian Agent."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from kindred_ai.application.health.service import get_health_service
from kindred_ai.application.inventory.service import get_inventory_service
from kindred_ai.application.memory.service import get_memory_service
from kindred_ai.application.security.service import get_security_service
from kindred_ai.presentation.api.app import create_app


class InventoryGuardianTests(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        root = Path(self._directory.name)
        os.environ["KINDRED_HEALTH_DB_PATH"] = str(root / "health.sqlite3")
        os.environ["KINDRED_MEMORY_DB_PATH"] = str(root / "memory.sqlite3")
        os.environ["KINDRED_SECURITY_DB_PATH"] = str(root / "security.sqlite3")
        os.environ["KINDRED_INVENTORY_DB_PATH"] = str(root / "inventory.sqlite3")
        os.environ["KINDRED_DISABLE_LLM"] = "true"
        for service in (get_health_service, get_memory_service, get_security_service, get_inventory_service):
            service.cache_clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        for service in (get_health_service, get_memory_service, get_security_service, get_inventory_service):
            service.cache_clear()
        for key in ("KINDRED_HEALTH_DB_PATH", "KINDRED_MEMORY_DB_PATH", "KINDRED_SECURITY_DB_PATH", "KINDRED_INVENTORY_DB_PATH", "KINDRED_DISABLE_LLM"):
            os.environ.pop(key, None)
        self._directory.cleanup()

    def test_inventory_and_low_supply_warning_are_available(self) -> None:
        inventory = self.client.get("/api/v1/inventory")
        supply = self.client.get("/api/v1/guardian/medication-supply")
        self.assertEqual(200, inventory.status_code)
        self.assertEqual(200, supply.status_code)
        metformin = next(item for item in supply.json() if item["medication_name"] == "Metformin")
        metformin_inventory = next(item for item in inventory.json() if item["medication_name"] == "Metformin")
        self.assertEqual(6, metformin["days_remaining"])
        self.assertTrue(metformin["refill_warning"])
        self.assertEqual("demo-schedule-metformin", metformin_inventory["schedule_id"])

    def test_guardian_creates_alert_and_requires_order_confirmation(self) -> None:
        analysis = self.client.post("/api/v1/guardian/analyze", json={"message": "Urgent: send your gift card details."})
        denied = self.client.post("/api/v1/guardian/replenishment-requests", json={"medication_name": "Metformin", "quantity": 60, "user_confirmed": False})
        confirmed = self.client.post("/api/v1/guardian/replenishment-requests", json={"medication_name": "Metformin", "quantity": 60, "user_confirmed": True})
        self.assertEqual("high", analysis.json()["event"]["risk_level"])
        self.assertEqual("open", analysis.json()["alert"]["status"])
        self.assertEqual(422, denied.status_code)
        self.assertEqual(201, confirmed.status_code)
        self.assertEqual("requested", confirmed.json()["status"])

    def test_logistics_manages_household_inventory_and_confirmed_requests(self) -> None:
        inventory = self.client.get("/api/v1/logistics/household-inventory")
        tea = next(item for item in inventory.json() if item["item_name"] == "Jasmine tea")
        denied = self.client.post(
            "/api/v1/logistics/purchase-requests",
            json={"item_name": "Jasmine tea", "quantity": 2, "user_confirmed": False},
        )
        confirmed = self.client.post(
            "/api/v1/logistics/purchase-requests",
            json={"item_name": "Jasmine tea", "quantity": 2, "user_confirmed": True},
        )
        reminder = self.client.post(
            "/api/v1/logistics/reminders",
            json={"title": "Buy Jasmine tea", "remind_at": "2026-07-26T09:00:00+02:00"},
        )
        self.assertEqual(200, inventory.status_code)
        self.assertTrue(tea["reorder_needed"])
        self.assertEqual(422, denied.status_code)
        self.assertEqual(201, confirmed.status_code)
        self.assertEqual("requested", confirmed.json()["status"])
        self.assertEqual(201, reminder.status_code)
        self.assertEqual("scheduled", reminder.json()["status"])


if __name__ == "__main__":
    unittest.main()
