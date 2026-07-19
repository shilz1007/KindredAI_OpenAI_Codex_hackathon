"""Tests for the Swagger-visible HTTP testing adapters."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from kindred_ai.application.health.service import get_health_service
from kindred_ai.application.memory.service import get_memory_service
from kindred_ai.application.security.service import get_security_service
from kindred_ai.presentation.api.app import create_app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        directory = Path(self._temporary_directory.name)
        os.environ["KINDRED_HEALTH_DB_PATH"] = str(directory / "health.sqlite3")
        os.environ["KINDRED_MEMORY_DB_PATH"] = str(directory / "memory.sqlite3")
        os.environ["KINDRED_SECURITY_DB_PATH"] = str(directory / "security.sqlite3")
        get_health_service.cache_clear()
        get_memory_service.cache_clear()
        get_security_service.cache_clear()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        get_health_service.cache_clear()
        get_memory_service.cache_clear()
        get_security_service.cache_clear()
        os.environ.pop("KINDRED_HEALTH_DB_PATH", None)
        os.environ.pop("KINDRED_MEMORY_DB_PATH", None)
        os.environ.pop("KINDRED_SECURITY_DB_PATH", None)
        self._temporary_directory.cleanup()

    def test_swagger_and_read_endpoints_are_available(self) -> None:
        self.assertEqual(200, self.client.get("/docs").status_code)
        self.assertEqual(200, self.client.get("/api/v1/health/medication-schedule").status_code)
        self.assertEqual("Anita", self.client.get("/api/v1/memory/profile").json()["preferred_name"])
        self.assertEqual(200, self.client.get("/api/v1/security/events").status_code)

    def test_write_endpoints_use_application_services(self) -> None:
        health_response = self.client.post(
            "/api/v1/health/medication-taken",
            json={"schedule_id": "demo-schedule-metformin", "note": "Swagger test"},
        )
        memory_response = self.client.post(
            "/api/v1/memory/memories",
            json={"content": "Anita likes tea.", "category": "preference", "importance": 3},
        )
        security_response = self.client.post(
            "/api/v1/security/analyze-message",
            json={"message": "Urgent: send gift card details."},
        )
        self.assertEqual(201, health_response.status_code)
        self.assertEqual(201, memory_response.status_code)
        self.assertEqual(201, security_response.status_code)


if __name__ == "__main__":
    unittest.main()
