import tempfile
import unittest
from pathlib import Path

from kindred_ai.application.communication.service import CommunicationService


class CommunicationMcpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = CommunicationService(Path(self.temp.name) / "communication.sqlite3")
        self.service.initialize()
    def tearDown(self): self.temp.cleanup()
    def test_contacts_and_approved_message_queue(self):
        self.assertIn("daughter", {contact["id"] for contact in self.service.list_contacts()})
        with self.assertRaisesRegex(ValueError, "Explicit user approval"):
            self.service.send_family_message("daughter", "Please call me.", False)
        self.assertEqual("queued", self.service.send_family_message("daughter", "Please call me.", True)["status"])

    def test_phone_book_resolves_family_relationship_and_queues_call(self):
        son = next(contact for contact in self.service.list_phone_book() if contact["relationship"] == "son")
        self.assertEqual("Rahim", son["display_name"])
        request = self.service.request_family_call("son")
        self.assertEqual("requested", request["status"])
        self.assertEqual("Rahim", request["display_name"])
        with self.assertRaisesRegex(ValueError, "not found"):
            self.service.request_family_call("neighbour")
