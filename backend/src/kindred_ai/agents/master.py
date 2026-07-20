"""Master Agent, the sole user-facing conversational coordinator."""

import json
import re
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from kindred_ai.agents.guardian import GuardianAgent
from kindred_ai.agents.companion import CompanionAgent
from kindred_ai.agents.logistics import LogisticsAgent
from kindred_ai.agents.research import ResearchAgent
from kindred_ai.application.ports.conversation_model import ConversationModel
from kindred_ai.application.ports.agent_router import AgentRoute, AgentRouter
from kindred_ai.application.conversation_state import InMemoryConversationState
from kindred_ai.infrastructure.observability import observation, record_output


class MasterAgent:
    """Routes Guardian workflows deterministically and speaks through a model."""

    def __init__(self, conversation_model: ConversationModel, guardian: GuardianAgent, router: AgentRouter, companion: CompanionAgent | None = None, logistics: LogisticsAgent | None = None, research: ResearchAgent | None = None, conversation_state: InMemoryConversationState | None = None, instruction: str = "") -> None:
        self._conversation_model = conversation_model
        self._guardian = guardian
        self._router = router
        self._companion = companion
        self._logistics = logistics
        self._research = research
        self._conversation_state = conversation_state or InMemoryConversationState()
        self._instruction = instruction

    def respond(self, message: str, *, session_id: str = "default") -> str:
        """Return an English reply informed by recent session and specialist context."""
        if not message.strip():
            raise ValueError("Message cannot be empty.")
        cleaned = message.strip()
        with observation("master.conversation", as_type="agent", input={"message": cleaned}, metadata={"session_id": session_id, "feature": "conversation"}) as trace:
            prior_context = self._conversation_state.recent_context(session_id)
            specialist_context = self._route_to_specialist(cleaned, session_id=session_id)
            if specialist_context.startswith("FINAL_REPLY: "):
                reply = specialist_context.removeprefix("FINAL_REPLY: ")
            else:
                reply = self._conversation_model.respond(
                instruction=(
                self._instruction + "\n\n"
                "Use these response-format and safety constraints. "
                "You are the only conversational agent. Use the specialist result below as factual context. "
                "Do not invent medication, order, or security facts. If a security alert exists, advise the user "
                "not to share sensitive details and to contact a trusted person. Reply only in clear English, even if the user's words are transcribed incorrectly or are in another language. "
                "Never reply in Bengali or mix languages. Continue the English conversation naturally. "
                "Keep the reply concise. For medication-supply questions, speak in calm, plain language that is easy for an older adult to hear and read. "
                "Only mention medicines with seven days or fewer remaining. State each in one short sentence: medicine name and days remaining. "
                "Do not mention medicines that are well stocked unless every medicine is well stocked, in which case say that plainly. "
                "Use no more than three short sentences before one clear question about refill help. "
                "For a recorded family call request, keep the response to the brief specialist wording and do not add technical system limitations. "
                "Never claim that a phone-book contact can be annotated, labelled, or edited unless the specialist result explicitly confirms it. "
                "Kindred can save contacts to its own prototype phone book through the routed Companion workflow. Do not describe this as operating the user's physical phone. "
                "Do not use Markdown, headings, asterisks, tables, or dense lists."
            ),
                user_message=cleaned,
                specialist_context=f"Recent conversation:\n{prior_context}\n\nSpecialist result:\n{specialist_context}",
                )
            reply = self._add_session_welcome(reply, session_id)
            reply = self._add_daily_check_in_after_completed_task(reply, session_id)
            self._conversation_state.append_turn(session_id, role="user", content=cleaned)
            self._conversation_state.append_turn(session_id, role="assistant", content=reply)
            record_output(trace, {"reply": reply})
            return reply

    def clear_conversation(self, session_id: str) -> None:
        """Remove one temporary browser session from the in-memory transcript."""
        self._conversation_state.clear(session_id)

    def welcome_thought(self) -> str:
        """Create one brief, fresh encouragement for Anita's Care Hub login."""
        with observation("master.welcome-thought", as_type="agent", input={"recipient": "Anita"}, metadata={"feature": "care-hub-welcome"}) as trace:
            thought = self._conversation_model.respond(
                instruction=(
                    self._instruction + "\n\n"
                    "Write one fresh, gentle English encouragement for Anita, an older adult. "
                    "Make it warm, hopeful, and easy to read. Use one sentence of 18 words or fewer. "
                    "Do not address Anita by name or use any person's name. "
                    "Do not mention medical advice, safety warnings, Kindred, or being an AI. "
                    "Return only the sentence, with no quotation marks or Markdown."
                ),
                user_message="Please choose a new encouragement for Anita's Care Hub.",
                specialist_context="No specialist data is needed.",
            )
            thought = re.sub(r"^\s*Anita\s*[,!:-]?\s*", "", thought, flags=re.IGNORECASE).strip()
            record_output(trace, {"thought": thought})
            return thought

    def daily_briefing(self, on_date: date | None = None) -> str:
        """Create a warm start-of-day greeting from approved specialist context."""
        local_date = on_date or datetime.now(ZoneInfo("Europe/Oslo")).date()
        personal_dates = self._companion.important_dates_for(local_date) if self._companion else []
        reminders = self._logistics.reminders() if self._logistics else []
        today_reminders = [item for item in reminders if item["remind_at"][:10] == local_date.isoformat()]
        medication_schedule = self._guardian.medication_schedule()
        context = {
            "date": local_date.isoformat(),
            "personal_or_special_dates": personal_dates,
            "today_reminders": today_reminders,
            "medications": medication_schedule,
        }
        with observation("master.daily-briefing", as_type="agent", input=context, metadata={"feature": "daily-briefing"}) as trace:
            reply = self._conversation_model.respond(
                instruction=(
                    self._instruction + "\n\n"
                    "Write a warm English-only start-of-day greeting for an older adult. "
                    "Write exactly two or three short, natural sentences. "
                    "First, say good morning and ask how the person is feeling. "
                    "Next, mention at most one supplied personal date, special date, reminder, or medicine item in a natural sentence. "
                    "If that item is a birthday, use the supplied person's name and offer one simple action: sending a message. "
                    "End with only one clear question. Do not repeat an offer to help, repeat a question, or list several possible tasks. "
                    "Mention only facts supplied in the specialist context. Do not use Markdown, headings, or Bengali."
                ),
                user_message="Start today's Care Hub greeting.",
                specialist_context=str(context),
            )
            record_output(trace, {"reply": reply})
            return reply

    def get_specialist_context(self, message: str) -> str:
        """Run the approved specialist workflow without generating a user-facing reply.

        The Realtime voice adapter uses this boundary when the Master model calls
        its Guardian consultation tool.  The adapter never receives direct MCP
        access.
        """
        if not message.strip():
            raise ValueError("Message cannot be empty.")
        return self._route_to_specialist(message.strip())

    def _route_to_specialist(self, message: str, *, session_id: str = "default") -> str:
        pending = self._conversation_state.pending_action(session_id)
        if pending and pending["kind"] == "phone_book_confirmation":
            return self._complete_phone_book_confirmation(message, session_id, pending)
        if pending and pending["kind"] == "family_message_confirmation":
            return self._complete_family_message_confirmation(message, session_id, pending)
        if pending and pending["kind"] == "contact_action_choice":
            return self._complete_contact_action_choice(message, session_id, pending)
        if pending and pending["kind"] == "household_purchase_confirmation":
            return self._complete_household_purchase_confirmation(message, session_id, pending)
        if pending and pending["kind"] == "medication_checklist":
            return self._complete_medication_checklist(message, session_id, pending)

        oslo_now = datetime.now(ZoneInfo("Europe/Oslo"))
        routing_message = (
            f"Current local date and time in Europe/Oslo: {oslo_now.isoformat()}. "
            f"User request: {message}"
        )
        if pending and pending["kind"] == "phone_book_details":
            routing_message = (
                "The user is providing details for a phone-book contact. "
                f"Current local date and time in Europe/Oslo: {oslo_now.isoformat()}. "
                "Extract the contact fields from this message: " + message
            )
        route = self._router.route(routing_message)
        with observation(f"agent.{route.agent}", as_type="agent", input={"intent": route.intent}, metadata={"agent": route.agent, "intent": route.intent}) as agent_trace:
            result = self._execute_route(route, message, session_id=session_id)
            record_output(agent_trace, result)
            return result

    def _execute_route(self, route: AgentRoute, message: str, *, session_id: str) -> str:
        if route.agent == "master":
            if route.intent == "current_time":
                now = datetime.now(ZoneInfo("Europe/Oslo"))
                return f"FINAL_REPLY: It is {now.strftime('%H:%M')} in Oslo."
            return "General safety guidance only. Do not access Security MCP records or create an alert."
        if route.agent == "guardian":
            return self._route_guardian(route, message, session_id=session_id)
        if route.agent == "companion":
            return self._route_companion(route, message, session_id=session_id)
        if route.agent == "logistics":
            return self._route_logistics(route, message, session_id=session_id)
        if route.agent == "research":
            return self._route_research(route, message)
        return "No specialist workflow is available for this request."

    def _route_research(self, route: AgentRoute, message: str) -> str:
        """Consult Tavily only through the catalog-authorized Research Agent."""
        if self._research is None:
            return "FINAL_REPLY: Live research is not available right now."
        if route.intent != "research_query":
            return "FINAL_REPLY: I could not identify a live-information question to research."
        try:
            answer = self._research.research(message)
        except RuntimeError as error:
            return f"FINAL_REPLY: {error}"
        return f"FINAL_REPLY: {answer.answer}"

    def _route_guardian(self, route: AgentRoute, message: str, *, session_id: str) -> str:
        if route.intent == "security_inbox":
            return f"Stored phone messages (newest first): {self._guardian.phone_messages()}"
        if route.intent == "medication_supply":
            return f"Medication supply: {self._guardian.medication_supply()}"
        if route.intent == "medication_status":
            status = self._guardian.medication_status_today()
            not_taken = status["not_taken"]
            if not_taken:
                summary = ", ".join(f"{dose['medication_name']} at {dose['scheduled_time']}" for dose in not_taken)
                return f"FINAL_REPLY: You have not recorded {summary} today."
            upcoming = status["upcoming"]
            if upcoming:
                next_dose = upcoming[0]
                return (
                    "FINAL_REPLY: You have recorded all medicine doses due so far today. "
                    f"Your next medicine is {next_dose['medication_name']} at {next_dose['scheduled_time']}."
                )
            return "FINAL_REPLY: You have recorded all medicine doses due so far today."
        if route.intent == "medication_taken":
            if not route.medication_name:
                return self._start_medication_checklist(route, session_id=session_id)
            if route.medication_report == "missed":
                if route.medication_time:
                    self._guardian.record_medication_missed(route.medication_name, route.medication_time)
                return (
                    f"I recorded {route.medication_name} as missed. For advice about a missed dose, "
                    "please check the medicine leaflet or ask your pharmacist."
                )
            result = self._guardian.record_medication_taken(route.medication_name)
            if result["status"] == "needs_clarification":
                return result["message"]
            supply = result["supply"]
            if supply and supply["refill_warning"]:
                return (
                    f"Taken dose recorded for {result['medication_name']}. "
                    f"{supply['days_remaining']} days of medicine remain. "
                    "Would you like to prepare a refill request?"
                )
            return f"Taken dose recorded for {result['medication_name']}."
        if route.intent == "medication_replenishment":
            if not self._is_explicit_purchase_confirmation(message):
                return "A medication refill requires explicit confirmation before it can be requested."
            if route.medication_name and route.quantity:
                request = self._guardian.request_medication_replenishment(
                    medication_name=route.medication_name.title(), quantity=route.quantity, user_confirmed=True,
                )
                return f"Confirmed replenishment request: {request}"
        result: dict[str, Any] = self._guardian.analyze_message(message)
        return f"Guardian safety result: {result}"

    def _start_medication_checklist(self, route: AgentRoute, *, session_id: str) -> str:
        """Ask one simple yes/no question for each due medication dose."""
        now = datetime.now(ZoneInfo("Europe/Oslo"))
        requested_time = route.medication_time
        due_doses: list[dict[str, str]] = []
        for schedule in self._guardian.medication_schedule():
            for scheduled_time in schedule["daily_times"]:
                if requested_time:
                    if scheduled_time != requested_time:
                        continue
                elif scheduled_time > now.strftime("%H:%M"):
                    continue
                due_doses.append({
                    "medication_name": schedule["medication_name"],
                    "scheduled_time": scheduled_time,
                })
        due_doses.sort(key=lambda dose: (dose["scheduled_time"], dose["medication_name"]))
        if not due_doses:
            if requested_time:
                return f"FINAL_REPLY: I could not find any medicine scheduled for {requested_time} today."
            return "FINAL_REPLY: There are no medicine doses scheduled before now today."
        first, remaining = due_doses[0], due_doses[1:]
        self._conversation_state.set_pending_action(session_id, {
            "kind": "medication_checklist",
            "current": json.dumps(first),
            "remaining": json.dumps(remaining),
            "recorded": json.dumps([]),
            "unrecorded": json.dumps([]),
        })
        if route.medication_report == "missed":
            return "FINAL_REPLY: " + (
                f"You mentioned a missed dose around {first['scheduled_time']}. "
                f"Did you take {first['medication_name']} at {first['scheduled_time']}?"
            )
        return f"FINAL_REPLY: Let us check your medicines one at a time. Did you take {first['medication_name']} at {first['scheduled_time']}?"

    def _complete_medication_checklist(self, message: str, session_id: str, pending: dict[str, str]) -> str:
        """Record only explicit yes answers; a no answer remains safely unrecorded."""
        answer = message.casefold()
        if re.search(r"\b(yes|yeah|yep|i did|taken|have taken)\b", answer):
            taken = True
        elif re.search(r"\b(no|nope|did not|didn't|not yet|forgot|missed)\b", answer):
            taken = False
        else:
            return "FINAL_REPLY: Please say yes if you took that medicine, or no if you did not."
        remaining = json.loads(pending["remaining"])
        recorded = json.loads(pending["recorded"])
        unrecorded = json.loads(pending["unrecorded"])
        dose = json.loads(pending["current"])
        label = f"{dose['medication_name']} at {dose['scheduled_time']}"
        if taken:
            self._guardian.record_medication_taken(dose["medication_name"])
            recorded.append(label)
        else:
            self._guardian.record_medication_missed(dose["medication_name"], dose["scheduled_time"])
            unrecorded.append(label)
        if remaining:
            next_dose, remaining = remaining[0], remaining[1:]
            self._conversation_state.set_pending_action(session_id, {
                "kind": "medication_checklist",
                "current": json.dumps(next_dose),
                "remaining": json.dumps(remaining),
                "recorded": json.dumps(recorded),
                "unrecorded": json.dumps(unrecorded),
            })
            return f"FINAL_REPLY: Did you take {next_dose['medication_name']} at {next_dose['scheduled_time']}?"
        self._conversation_state.clear_pending_action(session_id)
        parts: list[str] = []
        if recorded:
            parts.append("I recorded " + ", ".join(recorded) + ".")
        if unrecorded:
            parts.append("I marked " + ", ".join(unrecorded) + " as missed.")
            parts.append("For missed-dose advice, please check the medicine leaflet or ask your pharmacist.")
        return "FINAL_REPLY: " + " ".join(parts)

    def _route_companion(self, route: AgentRoute, message: str, *, session_id: str) -> str:
        if self._companion is None:
            return "Companion Agent is selected, but it is not available."
        if route.intent == "communication_call":
            if not route.contact_query:
                return "Who would you like to call? For example, say 'call my son' or 'call Sara'."
            request = self._companion.request_contact_call(route.contact_query)
            return f"Your message for {request['display_name']} has been recorded. I have asked your {request['relationship']} to call you."
        if route.intent == "contact_assistance":
            if not route.contact_query:
                return "FINAL_REPLY: Who would you like help contacting?"
            contact = self._companion.resolve_phone_book_contact(route.contact_query)
            self._conversation_state.set_pending_action(session_id, {
                "kind": "contact_action_choice",
                "contact_id": contact["id"],
                "display_name": contact["display_name"],
                "relationship": contact["relationship"],
                "purpose": message,
            })
            return (
                f"FINAL_REPLY: I found {contact['display_name']}, your {contact['relationship']}. "
                "Would you like me to record a call request or prepare a message?"
            )
        if route.intent == "family_message":
            if not route.contact_query:
                return "FINAL_REPLY: Who would you like to send this message to?"
            if self._is_explicit_family_message_request(message):
                contact = self._companion.resolve_phone_book_contact(route.contact_query)
                content = route.message_content or message
                self._companion.send_approved_family_message(contact["id"], content, True)
                return f"FINAL_REPLY: Your message for {contact['display_name']} has been recorded and sent."
            draft = self._companion.draft_family_message(route.contact_query, message)
            self._conversation_state.set_pending_action(session_id, {
                "kind": "family_message_confirmation",
                "contact_id": draft["contact_id"],
                "display_name": draft["display_name"],
                "relationship": draft["relationship"],
                "content": draft["content"],
            })
            return f"FINAL_REPLY: Here is a message for your {draft['relationship']}: {draft['content']} Would you like me to send it?"
        if route.intent == "family_birthday":
            contact_query = route.contact_query or "son"
            contact = self._companion.resolve_phone_book_contact(contact_query)
            if self._is_explicit_birthday_message(message):
                self._companion.queue_birthday_message(contact_query)
                return f"FINAL_REPLY: Message successfully sent to your {contact['relationship']}."
            return f"FINAL_REPLY: Today is your {contact['relationship']} {contact['display_name']}'s birthday. Would you like me to send birthday wishes?"
        if route.intent == "phone_book_contact":
            pending = self._conversation_state.pending_action(session_id)
            if not pending or pending["kind"] != "phone_book_details":
                self._conversation_state.set_pending_action(session_id, {"kind": "phone_book_details"})
                return "FINAL_REPLY: Of course. Please tell me the person's name, relationship to you, and phone number."
            details = {
                "kind": "phone_book_details",
                "display_name": route.contact_display_name.strip() if route.contact_display_name else pending.get("display_name", ""),
                "relationship": route.contact_query.strip().lower() if route.contact_query else pending.get("relationship", ""),
                "phone_number": route.contact_phone_number.strip() if route.contact_phone_number else pending.get("phone_number", ""),
            }
            missing = [
                label for label, value in (
                    ("the person's name", details["display_name"]),
                    ("their relationship to you", details["relationship"]),
                    ("their phone number", details["phone_number"]),
                ) if not value
            ]
            if missing:
                self._conversation_state.set_pending_action(session_id, details)
                return f"FINAL_REPLY: I have the other details. Please tell me {', '.join(missing)}."
            contact = {
                "kind": "phone_book_confirmation",
                "display_name": details["display_name"],
                "relationship": details["relationship"],
                "phone_number": details["phone_number"],
            }
            self._conversation_state.set_pending_action(session_id, contact)
            return (
                f"FINAL_REPLY: I have {contact['display_name']}, your {contact['relationship']}, "
                f"with phone number {contact['phone_number']}. Shall I save this contact?"
            )
        return self._companion.respond(message)

    def _route_logistics(self, route: AgentRoute, message: str, *, session_id: str) -> str:
        if self._logistics is None:
            return "Logistics Agent is selected, but it is not available."
        if route.intent == "household_purchase":
            if route.household_item_name and route.quantity:
                if not self._is_explicit_purchase_confirmation(message):
                    self._conversation_state.set_pending_action(session_id, {
                        "kind": "household_purchase_confirmation",
                        "item_name": route.household_item_name,
                        "quantity": str(route.quantity),
                    })
                    return f"FINAL_REPLY: I can request {route.quantity} {route.household_item_name}. Shall I place this simulated request?"
                request = self._logistics.request_purchase(
                    item_name=route.household_item_name, quantity=route.quantity, user_confirmed=True,
                )
                return f"FINAL_REPLY: Your request for {request['quantity']} {request['item_name']} has been recorded."
        if route.intent == "household_reminder":
            if route.reminder_title and route.remind_at:
                reminder = self._logistics.schedule_reminder(
                    title=route.reminder_title,
                    remind_at=self._normalize_remind_at(route.remind_at),
                )
                return f"Scheduled household reminder: {reminder}"
            return "Please provide a reminder title and a date and time with timezone."
        return f"Household inventory: {self._logistics.household_inventory()}"

    def _add_session_welcome(self, reply: str, session_id: str) -> str:
        """Greet only after the user starts a real conversation, never on login."""
        if not self._instruction or not self._conversation_state.claim_first_greeting(session_id):
            return reply
        hour = datetime.now(ZoneInfo("Europe/Oslo")).hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        return f"{greeting}. {reply}"

    def _add_daily_check_in_after_completed_task(self, reply: str, session_id: str) -> str:
        """Offer one relevant daily update after a successful user-requested action."""
        if not self._instruction or not self._is_completed_task(reply):
            return reply
        if not self._conversation_state.claim_daily_update(session_id):
            return reply
        local_date = datetime.now(ZoneInfo("Europe/Oslo")).date()
        personal_dates = self._companion.important_dates_for(local_date) if self._companion and hasattr(self._companion, "important_dates_for") else []
        reminders = self._logistics.reminders() if self._logistics and hasattr(self._logistics, "reminders") else []
        today_reminders = [item for item in reminders if item.get("remind_at", "")[:10] == local_date.isoformat()]
        if personal_dates:
            return (
                f"{reply} Also, {personal_dates[0]} "
                "Would you like me to send a message, or help with your medicines, groceries, or reminders?"
            )
        if today_reminders:
            return (
                f"{reply} Also, you have a reminder today: {today_reminders[0]['title']}. "
                "Would you like help with your medicines, groceries, or reminders?"
            )
        return f"{reply} Would you like help with your medicines, groceries, or reminders?"

    @staticmethod
    def _is_completed_task(reply: str) -> bool:
        """Recognize completed local prototype actions without treating questions as completion."""
        return bool(re.search(
            r"\b(has been saved|dose recorded|message successfully sent|has been recorded|scheduled|confirmed (?:replenishment|household) request)\b",
            reply,
            flags=re.IGNORECASE,
        ))

    @staticmethod
    def _is_explicit_purchase_confirmation(message: str) -> bool:
        """Policy check: an LLM route alone cannot authorize a purchase."""
        return bool(re.search(r"\b(confirm(?:ed)?|yes|go ahead|please request)\b", message, flags=re.IGNORECASE))

    @staticmethod
    def _is_explicit_family_message_request(message: str) -> bool:
        """A direct request to ask/tell/send a family contact is explicit local-queue approval."""
        return bool(re.search(r"\b(ask|tell|send)\b", message, flags=re.IGNORECASE))

    @staticmethod
    def _is_explicit_birthday_message(message: str) -> bool:
        """An informational birthday mention must not create a queued message."""
        return bool(re.search(r"\b(send|wish|message|greet|tell)\b", message, flags=re.IGNORECASE))

    @staticmethod
    def _normalize_remind_at(value: str) -> str:
        """Complete a router-produced time-only value using the supplied local-day context.

        Intent selection stays with the model. This is only date/time format
        normalization at the boundary before an MCP tool receives a datetime.
        """
        if not re.fullmatch(r"T\d{2}:\d{2}(?::\d{2})?", value):
            return value
        oslo = ZoneInfo("Europe/Oslo")
        local_now = datetime.now(oslo)
        local_time = time.fromisoformat(value.removeprefix("T"))
        return datetime.combine(local_now.date(), local_time, tzinfo=oslo).isoformat()

    def _complete_phone_book_confirmation(self, message: str, session_id: str, pending: dict[str, str]) -> str:
        """Save a collected contact only after a clear affirmative answer."""
        lowered = message.casefold().strip()
        if re.search(r"\b(yes|save|confirm|correct)\b", lowered):
            try:
                self._companion.add_phone_book_contact(
                    pending["display_name"], pending["relationship"], pending["phone_number"],
                )
            finally:
                self._conversation_state.clear_pending_action(session_id)
            return f"FINAL_REPLY: {pending['display_name']} has been saved in your phone book."
        if re.search(r"\b(no|cancel|don't|do not)\b", lowered):
            self._conversation_state.clear_pending_action(session_id)
            return "FINAL_REPLY: No contact was saved."
        return "FINAL_REPLY: Please say yes to save this contact, or no to cancel."

    def _complete_family_message_confirmation(self, message: str, session_id: str, pending: dict[str, str]) -> str:
        """Queue the already-approved draft exactly once, without asking Router to draft it again."""
        lowered = message.casefold().strip()
        if re.search(r"\b(yes|send|confirm|go ahead|please do)\b", lowered):
            try:
                self._companion.send_approved_family_message(pending["contact_id"], pending["content"], True)
            finally:
                self._conversation_state.clear_pending_action(session_id)
            return f"FINAL_REPLY: Your message for {pending['display_name']} has been recorded and sent."
        if re.search(r"\b(no|cancel|don't|do not)\b", lowered):
            self._conversation_state.clear_pending_action(session_id)
            return "FINAL_REPLY: I have not sent the message."
        return "FINAL_REPLY: Please say send to record this message, or cancel if you do not want to send it."

    def _complete_contact_action_choice(self, message: str, session_id: str, pending: dict[str, str]) -> str:
        """Continue a generic saved-contact request after the user chooses call or message."""
        lowered = message.casefold()
        if re.search(r"\b(call|phone)\b", lowered):
            try:
                request = self._companion.request_contact_call(pending["display_name"])
            finally:
                self._conversation_state.clear_pending_action(session_id)
            return (
                f"FINAL_REPLY: Your request for {request['display_name']} has been recorded. "
                f"I have asked your {request['relationship']} to call you."
            )
        if re.search(r"\b(message|text|sms)\b", lowered):
            draft = self._companion.draft_family_message(pending["display_name"], pending["purpose"])
            self._conversation_state.set_pending_action(session_id, {
                "kind": "family_message_confirmation",
                "contact_id": draft["contact_id"],
                "display_name": draft["display_name"],
                "relationship": draft["relationship"],
                "content": draft["content"],
            })
            return f"FINAL_REPLY: Here is the message: {draft['content']} Would you like me to send it?"
        return "FINAL_REPLY: Please say call or message."

    def _complete_household_purchase_confirmation(self, message: str, session_id: str, pending: dict[str, str]) -> str:
        """Finish a previously reviewed household request exactly once."""
        lowered = message.casefold().strip()
        if re.search(r"\b(yes|confirm|go ahead|request)\b", lowered):
            try:
                request = self._logistics.request_purchase(
                    item_name=pending["item_name"], quantity=int(pending["quantity"]), user_confirmed=True,
                )
            finally:
                self._conversation_state.clear_pending_action(session_id)
            return f"FINAL_REPLY: Your request for {request['quantity']} {request['item_name']} has been recorded."
        if re.search(r"\b(no|cancel|don't|do not)\b", lowered):
            self._conversation_state.clear_pending_action(session_id)
            return "FINAL_REPLY: I have not recorded a purchase request."
        return "FINAL_REPLY: Please say yes to record this purchase request, or no to cancel."
