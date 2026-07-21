"""Companion Agent orchestration over approved Memory and Communication MCPs."""
from difflib import SequenceMatcher
import re
from datetime import date, datetime
from kindred_ai.infrastructure.mcp_clients import CommunicationMcpClient, MemoryMcpClient
from kindred_ai.application.ports.conversation_model import ConversationModel


class CompanionAgent:
    """Provides social and emotional companionship through Memory MCP tools."""

    def __init__(self, memory: MemoryMcpClient, communication: CommunicationMcpClient, model: ConversationModel, instruction: str = "") -> None:
        self._memory, self._communication, self._model = memory, communication, model
        self._instruction = instruction

    def respond(self, message: str) -> str:
        profile, history, memories = self._memory.get_user_profile(), self._memory.retrieve_history(), self._memory.retrieve_memories(limit=20)
        return self._model.respond(
            instruction=(
                self._instruction + "\n\n"
                "Use the supplied Memory MCP context only; "
                "do not invent personal facts, special-day history, dates, or app capabilities. "
                "Do not claim to save, edit, label, annotate, or add notes to phone-book contacts. "
                "Phone-book actions must be performed by the Master Agent's routed Communication MCP workflow."
            ),
            user_message=message,
            specialist_context=f"Profile: {profile}; Saved memories: {memories}; Recent history: {history}",
        )

    def contacts(self): return self._communication.get_family_contacts()
    def phone_book(self): return self._communication.get_phone_book()
    def request_contact_call(self, contact_query: str): return self._communication.request_contact_call(contact_query)
    def add_phone_book_contact(self, display_name: str, relationship: str, phone_number: str):
        return self._communication.add_phone_book_contact(display_name, relationship, phone_number, True)
    def send_approved_family_message(self, contact_id: str, content: str, user_approved: bool):
        return self._communication.send_contact_message(contact_id, content, user_approved)

    def draft_family_message(self, contact_query: str, request: str) -> dict[str, str]:
        """Prepare, but never send, one warm family message for later confirmation."""
        contact = self.resolve_phone_book_contact(contact_query)
        content = self._model.respond(
            instruction=(
                self._instruction + "\n\n"
                "Draft one short, warm English message from Anita to the named family contact. "
                "Use the user's request as the purpose. Be supportive but do not make medical claims or diagnose anyone. "
                "Do not say that the message has been sent. Return only the message text, with no Markdown or quotation marks."
            ),
            user_message=request,
            specialist_context=f"Recipient: {contact['display_name']}, relationship: {contact['relationship']}.",
        )
        return {"contact_id": contact["id"], "display_name": contact["display_name"], "relationship": contact["relationship"], "content": content.strip()}

    def resolve_phone_book_contact(self, contact_query: str) -> dict:
        """Resolve a trusted contact from a name, relationship, or natural spoken phrase."""
        query = contact_query.strip().casefold()
        if not query:
            raise ValueError("A family contact name or relationship is required.")
        contacts = self.phone_book()
        exact_relationship = [item for item in contacts if item["relationship"].casefold() == query]
        exact_name = [item for item in contacts if item["display_name"].casefold() == query]
        matches = exact_relationship or exact_name
        if not matches:
            # Router entity extraction may retain surrounding words, for example
            # "my son who is depressed". Match complete relationship phrases,
            # preferring "son in law" over the shorter "son" relationship.
            normalized_query = re.sub(r"[^a-z0-9]+", " ", query).strip()
            relationship_matches = [
                item for item in contacts
                if re.search(
                    r"(?:^|\s)" + re.escape(re.sub(r"[^a-z0-9]+", " ", item["relationship"].casefold()).strip()) + r"(?:$|\s)",
                    normalized_query,
                )
            ]
            if relationship_matches:
                longest = max(len(item["relationship"]) for item in relationship_matches)
                matches = [item for item in relationship_matches if len(item["relationship"]) == longest]
        if not matches:
            matches = [
                item for item in contacts
                if query in item["display_name"].casefold() or query in item["relationship"].casefold()
            ]
        if not matches:
            # Voice transcription and spoken possessives can introduce a small
            # one-letter difference, such as "Smith's" for saved contact "Smit".
            # Accept only one clearly best near-name match; never guess when
            # two contacts are equally close.
            normalized_name = re.sub(r"(?:'s|s)\b$", "", re.sub(r"[^a-z0-9]+", "", query))
            scored = [
                (SequenceMatcher(None, normalized_name, re.sub(r"[^a-z0-9]+", "", item["display_name"].casefold())).ratio(), item)
                for item in contacts
            ]
            if scored:
                best_score = max(score for score, _ in scored)
                best = [item for score, item in scored if score == best_score]
                if len(normalized_name) >= 3 and best_score >= 0.82 and len(best) == 1:
                    matches = best
        if not matches:
            raise ValueError("Phone book contact was not found.")
        if len(matches) > 1:
            raise ValueError("More than one phone book contact matches; please use a specific name.")
        return matches[0]

    def queue_birthday_message(self, contact_query: str) -> dict:
        """Record an explicitly requested birthday wish in the local message queue."""
        contact = self.resolve_phone_book_contact(contact_query)
        message = f"Happy birthday, {contact['display_name']}. With all my love, Ma."
        queued = self.send_approved_family_message(contact["id"], message, True)
        return {"contact": contact, "message": queued}

    def important_dates_for(self, on_date: date) -> list[str]:
        """Find stored personal or special dates that match one calendar day."""
        matches: list[str] = []
        contacts = self.phone_book()
        for category in ("important_date", "event_date", "special_day"):
            for memory in self._memory.retrieve_memories(category=category):
                if _memory_matches_date(memory["content"], on_date):
                    matches.append(_personalize_family_date(memory["content"], contacts))
        return matches


def _memory_matches_date(content: str, on_date: date) -> bool:
    month_names = "January|February|March|April|May|June|July|August|September|October|November|December"
    match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(%s)(?:\s+(\d{4}))?\b" % month_names, content, flags=re.IGNORECASE)
    if match:
        try:
            parsed = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%d %B").date()
            return parsed.day == on_date.day and parsed.month == on_date.month and (not match.group(3) or int(match.group(3)) == on_date.year)
        except ValueError:
            return False
    every_month = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+of every month\b", content, flags=re.IGNORECASE)
    return bool(every_month and int(every_month.group(1)) == on_date.day)


def _personalize_family_date(content: str, contacts: list[dict]) -> str:
    """Use the phone book as the source of truth for close-family names."""
    normalized = content.casefold()
    if "birthday" not in normalized:
        return content
    for relationship in ("son", "daughter"):
        if relationship in normalized:
            contact = next((item for item in contacts if item["relationship"].casefold() == relationship), None)
            if contact:
                return f"Today is your {relationship} {contact['display_name']}'s birthday."
    return content
