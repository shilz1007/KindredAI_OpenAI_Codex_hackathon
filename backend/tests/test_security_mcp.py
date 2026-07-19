"""Integration tests for Security MCP's SQLite MVP."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from kindred_ai.application.security.service import SecurityService
from kindred_ai.infrastructure.security.sqlite_repository import SqliteSecurityRepository


class SecurityMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "security.sqlite3"
        self.repository = SqliteSecurityRepository(self.database_path)
        self.repository.initialize()
        self.service = SecurityService(self.repository)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_migrations_and_seed_are_idempotent(self) -> None:
        self.repository.initialize()
        with closing(sqlite3.connect(self.database_path)) as connection:
            versions = connection.execute("SELECT version FROM schema_migrations").fetchall()
            events = connection.execute("SELECT COUNT(*) FROM security_events").fetchone()[0]
        self.assertEqual([("001_initial.sql",), ("002_phone_messages.sql",), ("003_allow_critical_risk.sql",)], versions)
        self.assertEqual(2, events)

    def test_high_risk_message_records_signals(self) -> None:
        event = self.service.analyze_message("Urgent: send your gift card and OTP now.")
        self.assertEqual("high", event.risk_level)
        self.assertEqual(("gift card", "otp", "urgent"), event.matched_signals)

    def test_phone_code_scam_wording_is_high_risk(self) -> None:
        event = self.service.analyze_message("Someone called saying I must share the code sent to my text. Is it safe?")
        self.assertEqual("high", event.risk_level)
        self.assertEqual(("share the code", "code sent"), event.matched_signals)

    def test_alert_is_created_for_known_event(self) -> None:
        event = self.service.analyze_message("Please share your password.")
        alert = self.service.create_security_alert(event_id=event.id, severity="high")
        self.assertEqual(event.id, alert.event_id)
        self.assertEqual("open", alert.status)

    def test_unknown_event_and_empty_message_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            self.service.analyze_message(" ")
        with self.assertRaisesRegex(ValueError, "was not found"):
            self.service.create_security_alert(event_id="missing", severity="high")

    def test_events_are_returned_newest_first(self) -> None:
        self.service.analyze_message("A new message arrived.")
        events = self.service.get_security_events(limit=3)
        self.assertEqual("A new message arrived.", events[0].message)

    def test_phone_messages_are_returned_newest_first(self) -> None:
        first = self.repository.add_phone_message(message_id="first", message="First message", received_at=datetime.now(UTC))
        second = self.repository.add_phone_message(message_id="second", message="Second message", received_at=datetime.now(UTC))
        messages = self.service.get_phone_messages(limit=2)
        self.assertEqual("Second message", messages[0].message)
        self.assertEqual("First message", messages[1].message)

    def test_critical_risk_events_are_supported(self) -> None:
        event = self.repository.add_event(
            event_id="critical-event", message="Critical test", risk_level="critical",
            matched_signals=("test",), created_at=datetime.now(UTC),
        )
        self.assertEqual("critical", event.risk_level)


if __name__ == "__main__":
    unittest.main()
