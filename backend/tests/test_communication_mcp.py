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
            self.service.send_contact_message("daughter", "Please call me.", False)
        self.assertEqual("queued", self.service.send_contact_message("daughter", "Please call me.", True)["status"])

    def test_phone_book_resolves_family_relationship_and_queues_call(self):
        son = self.service.add_phone_book_contact("John Baker", "son", "+4790011222", True)
        self.assertEqual("John Baker", son["display_name"])
        request = self.service.request_contact_call("son")
        self.assertEqual("requested", request["status"])
        self.assertEqual("John Baker", request["display_name"])
        natural_request = self.service.request_contact_call("please ask my son to call me back")
        self.assertEqual("John Baker", natural_request["display_name"])
        with self.assertRaisesRegex(ValueError, "not found"):
            self.service.request_contact_call("neighbour")

    def test_phone_book_contact_can_be_added_for_simulated_communication(self):
        contact = self.service.add_phone_book_contact("Maya", "neighbour", "+4790011223", True)
        self.assertEqual("Maya", contact["display_name"])
        self.assertTrue(contact["approved_for_calls"])
        self.assertIn(contact["id"], {item["id"] for item in self.service.list_phone_book()})

    def test_any_saved_phone_book_contact_can_receive_a_simulated_message_or_call(self):
        mechanic = self.service.add_phone_book_contact("Simone", "mechanic", "+4790011224", True)
        message = self.service.send_contact_message(mechanic["id"], "Please call me about my car.", True)
        call = self.service.request_contact_call("my mechanic")
        self.assertEqual("queued", message["status"])
        self.assertEqual("Simone", call["display_name"])
