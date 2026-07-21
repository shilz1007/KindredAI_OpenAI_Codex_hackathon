"""Tests for Master Agent coordination and specialist workflows."""

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from kindred_ai.agents.master import MasterAgent
from kindred_ai.application.ports.agent_router import AgentRoute
from kindred_ai.application.health.service import get_health_service
from kindred_ai.application.inventory.service import get_inventory_service
from kindred_ai.application.security.service import get_security_service
from kindred_ai.application.guardian import get_guardian_agent


class MasterAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        root = Path(self._directory.name)
        os.environ["KINDRED_HEALTH_DB_PATH"] = str(root / "health.sqlite3")
        os.environ["KINDRED_INVENTORY_DB_PATH"] = str(root / "inventory.sqlite3")
        os.environ["KINDRED_SECURITY_DB_PATH"] = str(root / "security.sqlite3")
        os.environ["KINDRED_DISABLE_LLM"] = "true"
        for service in (get_health_service, get_inventory_service, get_security_service):
            service.cache_clear()

    def tearDown(self) -> None:
        for service in (get_health_service, get_inventory_service, get_security_service):
            service.cache_clear()
        for key in ("KINDRED_HEALTH_DB_PATH", "KINDRED_INVENTORY_DB_PATH", "KINDRED_SECURITY_DB_PATH", "KINDRED_DISABLE_LLM"):
            os.environ.pop(key, None)
        self._directory.cleanup()

    def test_master_routes_guardian_workflows_to_a_conversation_model(self) -> None:
        class FakeConversationModel:
            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                return specialist_context

        class FakeRouter:
            def route(self, message: str) -> AgentRoute:
                lowered = message.lower()
                if "days" in lowered or "supply" in lowered:
                    return AgentRoute(agent="guardian", intent="medication_supply", language="en", medication_name=None, quantity=None)
                if "order" in lowered:
                    return AgentRoute(agent="guardian", intent="medication_replenishment", language="en", medication_name="Metformin", quantity=60)
                return AgentRoute(agent="guardian", intent="security_review", language="en", medication_name=None, quantity=None)

        master = MasterAgent(FakeConversationModel(), get_guardian_agent(), FakeRouter())
        self.assertIn("'risk_level': 'high'", master.respond("Urgent: send your gift card details now."))
        self.assertIn("'days_remaining': 6", master.respond("show medication supply"))
        self.assertIn("'days_remaining': 6", master.respond("How many days of Metformin do I have left?"))
        self.assertIn("'status': 'requested'", master.respond("confirm order Metformin 60"))
        self.assertIn("'status': 'requested'", master.respond("Please confirm an order for 60 Metformin tablets."))

    def test_master_delegates_to_companion_and_logistics_and_keeps_session_context(self) -> None:
        class RecordingConversationModel:
            def __init__(self) -> None:
                self.contexts: list[str] = []

            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                self.contexts.append(specialist_context)
                return f"reply to {user_message}"

        class FakeRouter:
            def route(self, message: str) -> AgentRoute:
                if "tea" in message.lower():
                    return AgentRoute(agent="logistics", intent="household_inventory", language="en", medication_name=None, quantity=None)
                if "call" in message.lower():
                    return AgentRoute(agent="companion", intent="communication_call", language="en", medication_name=None, quantity=None, contact_query="son")
                return AgentRoute(agent="companion", intent="general_companionship", language="en", medication_name=None, quantity=None)

        class FakeCompanion:
            def respond(self, message: str) -> str:
                return f"Companion context for {message}"

            def request_contact_call(self, contact_query: str) -> dict[str, str]:
                return {"display_name": "Rahim", "relationship": "son"}

        class FakeLogistics:
            def household_inventory(self):
                return [{"item_name": "Jasmine tea", "reorder_needed": True}]

        model = RecordingConversationModel()
        master = MasterAgent(model, get_guardian_agent(), FakeRouter(), FakeCompanion(), FakeLogistics())
        self.assertEqual("reply to I feel lonely", master.respond("I feel lonely", session_id="browser-1"))
        self.assertEqual("reply to Do I need tea?", master.respond("Do I need tea?", session_id="browser-1"))
        self.assertIn("Companion context for I feel lonely", model.contexts[0])
        self.assertIn("Jasmine tea", model.contexts[1])
        self.assertIn("User: I feel lonely", model.contexts[1])
        self.assertIn("Assistant: reply to I feel lonely", model.contexts[1])
        self.assertEqual("reply to Call my son", master.respond("Call my son", session_id="browser-1"))
        self.assertIn("Your message for Rahim has been recorded", model.contexts[2])
        master.clear_conversation("browser-1")
        master.respond("Fresh conversation", session_id="browser-1")
        self.assertNotIn("User: I feel lonely", model.contexts[3])

    def test_master_reads_stored_phone_messages_only_for_security_inbox_route(self) -> None:
        class FakeConversationModel:
            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                return specialist_context

        class InboxRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(agent="guardian", intent="security_inbox", language="en", medication_name=None, quantity=None)

        class InboxGuardian:
            def phone_messages(self, *, limit: int = 10) -> list[dict[str, str]]:
                return [{"message": "Hi Anita, this is Sara. I will visit you on Sunday afternoon. Love you!", "risk_level": "low"}]

        reply = MasterAgent(FakeConversationModel(), InboxGuardian(), InboxRouter()).respond("Do I have new messages?")
        self.assertIn("Sara", reply)
        self.assertIn("Sunday afternoon", reply)

    def test_master_generates_a_short_welcome_thought_without_specialist_routing(self) -> None:
        class FakeConversationModel:
            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                self.instruction = instruction
                self.user_message = user_message
                self.specialist_context = specialist_context
                return "A little kindness can brighten the whole day."

        class RouterThatMustNotRun:
            def route(self, message: str) -> AgentRoute:
                raise AssertionError("Welcome thoughts must not invoke an MCP-owning specialist.")

        model = FakeConversationModel()
        master = MasterAgent(model, get_guardian_agent(), RouterThatMustNotRun())
        self.assertEqual("A little kindness can brighten the whole day.", master.welcome_thought())
        self.assertIn("one sentence", model.instruction)
        self.assertEqual("No specialist data is needed.", model.specialist_context)

    def test_master_records_a_named_taken_dose_and_offers_refill_when_low(self) -> None:
        class FakeConversationModel:
            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                return specialist_context

        class DoseRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(agent="guardian", intent="medication_taken", language="en", medication_name="Metformin", quantity=None)

        class DoseGuardian:
            def record_medication_taken(self, medication_name: str | None) -> dict[str, object]:
                return {"status": "recorded", "medication_name": medication_name, "record": {}, "supply": {"days_remaining": 6, "refill_warning": True}}

        reply = MasterAgent(FakeConversationModel(), DoseGuardian(), DoseRouter()).respond("I have taken my Metformin today.")
        self.assertIn("Taken dose recorded for Metformin", reply)
        self.assertIn("6 days", reply)
        self.assertIn("refill request", reply)

    def test_master_checks_due_medicines_one_at_a_time_before_recording(self) -> None:
        class Model:
            def respond(self, **_: object) -> str:
                raise AssertionError("Checklist replies are generated by Guardian orchestration.")

        class MedicationRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="guardian", intent="medication_taken", language="en",
                    medication_name=None, medication_time="08:00", medication_report="taken", quantity=None,
                )

        class ChecklistGuardian:
            def __init__(self) -> None:
                self.recorded: list[str] = []

            def medication_schedule(self) -> list[dict[str, object]]:
                return [
                    {"medication_name": "Metformin", "daily_times": ["08:00", "20:00"]},
                    {"medication_name": "Vitamin D", "daily_times": ["08:00"]},
                ]

            def record_medication_taken(self, medication_name: str) -> dict[str, object]:
                self.recorded.append(medication_name)
                return {"status": "recorded"}

        guardian = ChecklistGuardian()
        master = MasterAgent(Model(), guardian, MedicationRouter())
        session_id = "medication-check"
        self.assertEqual(
            "Let us check your medicines one at a time. Did you take Metformin at 08:00?",
            master.respond("I have taken all my medication today", session_id=session_id),
        )
        self.assertEqual("Did you take Vitamin D at 08:00?", master.respond("yes", session_id=session_id))
        self.assertEqual(
            "I recorded Metformin at 08:00, Vitamin D at 08:00.",
            master.respond("yes", session_id=session_id),
        )
        self.assertEqual(["Metformin", "Vitamin D"], guardian.recorded)

    def test_master_persists_reported_missed_doses_without_recording_them_as_taken(self) -> None:
        class Model:
            def respond(self, **_: object) -> str:
                raise AssertionError("Checklist replies are generated by Guardian orchestration.")

        class MissedDoseRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="guardian", intent="medication_taken", language="en",
                    medication_name=None, medication_time="08:00", medication_report="missed", quantity=None,
                )

        class ChecklistGuardian:
            def __init__(self) -> None:
                self.missed: list[tuple[str, str]] = []

            def medication_schedule(self) -> list[dict[str, object]]:
                return [{"medication_name": "Metformin", "daily_times": ["08:00"]}]

            def record_medication_taken(self, medication_name: str) -> dict[str, object]:
                raise AssertionError("A reported missed dose must not be recorded as taken.")

            def record_medication_missed(self, medication_name: str, scheduled_time: str) -> dict[str, str]:
                self.missed.append((medication_name, scheduled_time))
                return {"status": "missed"}

        guardian = ChecklistGuardian()
        master = MasterAgent(Model(), guardian, MissedDoseRouter())
        session_id = "missed-dose"
        self.assertIn("missed dose around 08:00", master.respond("I forgot my 8 AM medicines", session_id=session_id))
        reply = master.respond("no", session_id=session_id)
        self.assertIn("marked Metformin at 08:00 as missed", reply)
        self.assertIn("medicine leaflet", reply)
        self.assertEqual([("Metformin", "08:00")], guardian.missed)

    def test_master_uses_phone_book_name_and_queues_explicit_birthday_wish(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("A confirmed family-message result should be returned directly.")

        class BirthdayRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="companion",
                    intent="family_birthday",
                    language="en",
                    medication_name=None,
                    quantity=None,
                    contact_query="son",
                )

        class PhoneBookCompanion:
            def __init__(self) -> None:
                self.queued_for: str | None = None

            def resolve_phone_book_contact(self, query: str) -> dict[str, str]:
                self.resolved_query = query
                return {"id": "john", "display_name": "John Baker", "relationship": "son"}

            def queue_birthday_message(self, query: str) -> dict[str, object]:
                self.queued_for = query
                return {"contact": {"display_name": "John Baker"}, "message": {"status": "queued"}}

        companion = PhoneBookCompanion()
        master = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), BirthdayRouter(), companion)
        self.assertEqual(
            "Message successfully sent to your son.",
            master.respond("Please send birthday wishes to my son."),
        )
        self.assertEqual("son", companion.queued_for)

        informational_reply = master.respond("It is my son's birthday today.")
        self.assertEqual("Today is your son John Baker's birthday. Would you like me to send birthday wishes?", informational_reply)

    def test_master_collects_and_confirms_phone_book_contact(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("Phone-book workflow replies are direct and must not be invented by the model.")

        class ContactRouter:
            def route(self, message: str) -> AgentRoute:
                if "providing details" in message:
                    return AgentRoute(
                        agent="companion", intent="phone_book_contact", language="en",
                        medication_name=None, quantity=None, contact_display_name="John Baker",
                        contact_query="son", contact_phone_number="+4790011222",
                    )
                return AgentRoute(
                    agent="companion", intent="phone_book_contact", language="en",
                    medication_name=None, quantity=None,
                )

        class PhoneBookCompanion:
            def __init__(self) -> None:
                self.saved: tuple[str, str, str] | None = None

            def add_phone_book_contact(self, name: str, relationship: str, phone: str) -> dict[str, str]:
                self.saved = (name, relationship, phone)
                return {"display_name": name}

        companion = PhoneBookCompanion()
        master = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), ContactRouter(), companion)
        self.assertEqual(
            "Of course. Please tell me the person's name, relationship to you, and phone number.",
            master.respond("Can you save a contact in the phone book for me?", session_id="contact-flow"),
        )
        self.assertEqual(
            "I have John Baker, your son, with phone number +4790011222. Shall I save this contact?",
            master.respond("John Baker, my son, +47 900 11 222.", session_id="contact-flow"),
        )
        self.assertEqual(
            "John Baker has been saved in your phone book.",
            master.respond("Yes, save it.", session_id="contact-flow"),
        )
        self.assertEqual(("John Baker", "son", "+4790011222"), companion.saved)

    def test_master_keeps_partial_phone_book_details_and_only_requests_the_missing_field(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("Phone-book workflow replies are direct and must not be invented by the model.")

        class ContactRouter:
            def route(self, message: str) -> AgentRoute:
                if "900 11 222" in message:
                    return AgentRoute(
                        agent="companion", intent="phone_book_contact", language="en",
                        medication_name=None, quantity=None, contact_display_name="Smith",
                        contact_query=None, contact_phone_number="+4790011222",
                    )
                return AgentRoute(
                    agent="companion", intent="phone_book_contact", language="en",
                    medication_name=None, quantity=None, contact_display_name=None,
                    contact_query="friend", contact_phone_number=None,
                )

        master = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), ContactRouter(), object())
        self.assertIn("name, relationship", master.respond("Save a phone number.", session_id="partial-contact"))
        self.assertEqual(
            "I have the other details. Please tell me their relationship to you.",
            master.respond("The name is Smith, he is a friend, and his phone number is +47 900 11 222.", session_id="partial-contact"),
        )
        self.assertEqual(
            "I have Smith, your friend, with phone number +4790011222. Shall I save this contact?",
            master.respond("He is a friend.", session_id="partial-contact"),
        )

    def test_master_queues_the_confirmed_family_message_without_redrafting(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("Family-message confirmation must use the stored draft directly.")

        class MessageRouter:
            def __init__(self) -> None:
                self.calls = 0

            def route(self, message: str) -> AgentRoute:
                self.calls += 1
                return AgentRoute(
                    agent="companion", intent="family_message", language="en",
                    medication_name=None, quantity=None, contact_query="son",
                )

        class MessageCompanion:
            def __init__(self) -> None:
                self.drafts = 0
                self.sent: list[tuple[str, str, bool]] = []

            def draft_family_message(self, contact_query: str, request: str) -> dict[str, str]:
                self.drafts += 1
                return {
                    "contact_id": "son", "display_name": "John Baker", "relationship": "son",
                    "content": "I am thinking of you today. Please remember that you are loved.",
                }

            def send_approved_family_message(self, contact_id: str, content: str, approved: bool) -> dict[str, str]:
                self.sent.append((contact_id, content, approved))
                return {"status": "queued"}

        router, companion = MessageRouter(), MessageCompanion()
        master = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), router, companion)
        session_id = "encouragement-message"
        draft_reply = master.respond("Please write an encouraging message for my son.", session_id=session_id)
        sent_reply = master.respond("Send this message.", session_id=session_id)

        self.assertIn("Please remember that you are loved", draft_reply)
        self.assertEqual("Your message for John Baker has been recorded and sent.", sent_reply)
        self.assertEqual(1, companion.drafts)
        self.assertEqual(1, router.calls)
        self.assertEqual([("son", "I am thinking of you today. Please remember that you are loved.", True)], companion.sent)

    def test_companion_does_not_invent_phone_book_note_capabilities(self) -> None:
        class FakeMemory:
            def get_user_profile(self): return {}
            def retrieve_history(self): return []
            def retrieve_memories(self, **_: object): return []

        class FakeCommunication:
            pass

        class RecordingModel:
            def respond(self, **kwargs: object) -> str:
                self.instruction = str(kwargs["instruction"])
                return "I can help with supported actions."

        from kindred_ai.agents.companion import CompanionAgent
        model = RecordingModel()
        CompanionAgent(FakeMemory(), FakeCommunication(), model).respond("Add a note to Jason's contact.")
        self.assertIn("Do not claim to save, edit, label, annotate, or add notes", model.instruction)

    def test_companion_resolves_a_relationship_inside_a_natural_phrase(self) -> None:
        class FakeMemory:
            pass

        class FakeCommunication:
            def get_phone_book(self):
                return [
                    {"id": "son", "display_name": "John Baker", "relationship": "son"},
                    {"id": "son-in-law", "display_name": "Jonathon", "relationship": "son in law"},
                ]

        class FakeModel:
            pass

        from kindred_ai.agents.companion import CompanionAgent
        companion = CompanionAgent(FakeMemory(), FakeCommunication(), FakeModel())
        self.assertEqual("John Baker", companion.resolve_phone_book_contact("my son who is depressed")["display_name"])
        self.assertEqual("Jonathon", companion.resolve_phone_book_contact("my son-in-law needs encouragement")["display_name"])

    def test_companion_accepts_one_clear_near_name_match_for_voice_input(self) -> None:
        class FakeMemory:
            pass

        class FakeCommunication:
            def get_phone_book(self):
                return [{"id": "smit", "display_name": "Smit", "relationship": "friend"}]

        from kindred_ai.agents.companion import CompanionAgent
        companion = CompanionAgent(FakeMemory(), FakeCommunication(), object())
        self.assertEqual("Smit", companion.resolve_phone_book_contact("Smith's")["display_name"])

    def test_master_normalizes_router_time_only_reminder_for_today(self) -> None:
        class FakeConversationModel:
            def respond(self, **kwargs: object) -> str:
                return str(kwargs["specialist_context"])

        class ReminderRouter:
            def route(self, message: str) -> AgentRoute:
                self.message = message
                return AgentRoute(
                    agent="logistics", intent="household_reminder", language="en",
                    medication_name=None, quantity=None,
                    reminder_title="Call Simone the mechanic", remind_at="T22:00:00",
                )

        class FakeLogistics:
            def schedule_reminder(self, *, title: str, remind_at: str) -> dict[str, str]:
                self.title, self.remind_at = title, remind_at
                return {"title": title, "remind_at": remind_at, "status": "scheduled"}

        router, logistics = ReminderRouter(), FakeLogistics()
        master = MasterAgent(FakeConversationModel(), get_guardian_agent(), router, logistics=logistics)
        reply = master.respond("Can you set a reminder for me today at 10:00 p.m. to call Simone the mechanic?")
        self.assertIn("Current local date and time in Europe/Oslo", router.message)
        self.assertIn("Call Simone the mechanic", reply)
        self.assertRegex(logistics.remind_at, r"^\d{4}-\d{2}-\d{2}T22:00:00[+-]\d{2}:\d{2}$")

    def test_master_daily_briefing_uses_specialist_context_only(self) -> None:
        class RecordingConversationModel:
            def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
                self.instruction = instruction
                self.context = specialist_context
                return "Good morning. How are you feeling today?"

        class FakeCompanion:
            def important_dates_for(self, on_date: date) -> list[str]:
                return ["Anita's son's birthday is on 20 July."]

        class FakeGuardian:
            def medication_schedule(self) -> list[dict[str, object]]:
                return [{"medication_name": "Metformin", "daily_times": ["08:00"]}]

        class FakeLogistics:
            def reminders(self) -> list[dict[str, str]]:
                return [{"title": "Buy tea", "remind_at": "2026-07-20T10:00:00+02:00"}]

        class RouterThatMustNotRun:
            def route(self, message: str) -> AgentRoute:
                raise AssertionError("Daily briefing should call specialists directly through approved agents.")

        model = RecordingConversationModel()
        master = MasterAgent(model, FakeGuardian(), RouterThatMustNotRun(), FakeCompanion(), FakeLogistics())
        self.assertEqual("Good morning. How are you feeling today?", master.daily_briefing(date(2026, 7, 20)))
        self.assertIn("son's birthday", model.context)
        self.assertIn("Buy tea", model.context)
        self.assertIn("exactly two or three short", model.instruction)
        self.assertIn("Do not repeat an offer", model.instruction)

    def test_master_reads_persisted_medication_status_without_starting_a_checklist(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("Medication status is a direct specialist result.")

        class StatusRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="guardian", intent="medication_status", language="en",
                    medication_name=None, quantity=None,
                )

        class StatusGuardian:
            def medication_status_today(self) -> dict[str, list[dict[str, str]]]:
                return {"not_taken": [{"medication_name": "Metformin", "scheduled_time": "08:00"}], "upcoming": []}

        reply = MasterAgent(ModelThatMustNotRun(), StatusGuardian(), StatusRouter()).respond("What medicine have I not taken today?")
        self.assertEqual("You have not recorded Metformin at 08:00 today.", reply)

    def test_next_medicine_uses_the_next_scheduled_dose_not_an_unrecorded_one(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("Medication status is a direct specialist result.")

        class StatusRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="guardian", intent="medication_status", language="en",
                    medication_name=None, quantity=None,
                )

        class StatusGuardian:
            def medication_status_today(self) -> dict[str, list[dict[str, str]]]:
                return {
                    "not_taken": [{"medication_name": "Levothyroxine", "scheduled_time": "10:00"}],
                    "upcoming": [{"medication_name": "Atorvastatin", "scheduled_time": "20:30"}],
                }

        reply = MasterAgent(ModelThatMustNotRun(), StatusGuardian(), StatusRouter()).respond("When is my next medicine?")
        self.assertEqual("Your next medicine is Atorvastatin at 20:30.", reply)

    def test_master_answers_current_time_from_its_oslo_context(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("Current time is a direct Master result.")

        class TimeRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="master", intent="current_time", language="en",
                    medication_name=None, quantity=None,
                )

        reply = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), TimeRouter()).respond("What time is it now?")
        self.assertRegex(reply, r"^It is \d{2}:\d{2} in Oslo\.$")

    def test_master_sends_a_direct_family_message_request_without_redrafting(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("An explicit send request must not be redrafted.")

        class MessageRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="companion", intent="family_message", language="en",
                    medication_name=None, quantity=None, contact_query="son",
                    message_content="Please send me a reminder at 10 PM to take my medicine.",
                )

        class Companion:
            def resolve_phone_book_contact(self, query: str) -> dict[str, str]:
                return {"id": "son", "display_name": "John Baker", "relationship": "son"}

            def send_approved_family_message(self, contact_id: str, content: str, approved: bool) -> dict[str, str]:
                self.sent = (contact_id, content, approved)
                return {"status": "queued"}

        companion = Companion()
        reply = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), MessageRouter(), companion).respond(
            "Can you ask my son to send me a message at 10 PM to take my medicine?",
        )
        self.assertEqual("Your message for John Baker has been recorded and sent.", reply)
        self.assertEqual(("son", "Please send me a reminder at 10 PM to take my medicine.", True), companion.sent)

    def test_master_offers_call_or_message_for_a_generic_saved_contact(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("The contact-action choice is a direct workflow.")

        class ContactRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="companion", intent="contact_assistance", language="en",
                    medication_name=None, quantity=None, contact_query="mechanic",
                )

        class ContactCompanion:
            def resolve_phone_book_contact(self, query: str) -> dict[str, str]:
                return {"id": "simone", "display_name": "Simone", "relationship": "mechanic"}

            def request_contact_call(self, query: str) -> dict[str, str]:
                self.called = query
                return {"display_name": "Simone", "relationship": "mechanic"}

        companion = ContactCompanion()
        master = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), ContactRouter(), companion)
        self.assertEqual(
            "I found Simone, your mechanic. Would you like me to record a call request or prepare a message?",
            master.respond("I need my car fixed.", session_id="mechanic"),
        )
        self.assertEqual(
            "Your request for Simone has been recorded. I have asked your mechanic to call you.",
            master.respond("Please call her.", session_id="mechanic"),
        )
        self.assertEqual("Simone", companion.called)

    def test_master_completes_a_confirmed_household_purchase_once(self) -> None:
        class ModelThatMustNotRun:
            def respond(self, **_: object) -> str:
                raise AssertionError("Purchase confirmations are direct specialist results.")

        class PurchaseRouter:
            def route(self, message: str) -> AgentRoute:
                return AgentRoute(
                    agent="logistics", intent="household_purchase", language="en",
                    medication_name=None, quantity=2, household_item_name="loaves of bread",
                )

        class Logistics:
            def request_purchase(self, *, item_name: str, quantity: int, user_confirmed: bool) -> dict[str, object]:
                self.request = (item_name, quantity, user_confirmed)
                return {"item_name": item_name, "quantity": quantity, "status": "requested"}

        logistics = Logistics()
        master = MasterAgent(ModelThatMustNotRun(), get_guardian_agent(), PurchaseRouter(), logistics=logistics)
        self.assertIn("Shall I place", master.respond("Please buy 2 loaves of bread.", session_id="purchase"))
        self.assertEqual(
            "Your request for 2 loaves of bread has been recorded.",
            master.respond("Yes please request these exact items now.", session_id="purchase"),
        )
        self.assertEqual(("loaves of bread", 2, True), logistics.request)
