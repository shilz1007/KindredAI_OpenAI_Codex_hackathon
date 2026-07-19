"""Companion Agent orchestration over approved Memory and Communication MCPs."""
from kindred_ai.infrastructure.mcp_clients import CommunicationMcpClient, MemoryMcpClient
from kindred_ai.application.ports.conversation_model import ConversationModel


class CompanionAgent:
    """Provides social and emotional companionship through Memory MCP tools."""

    def __init__(self, memory: MemoryMcpClient, communication: CommunicationMcpClient, model: ConversationModel) -> None:
        self._memory, self._communication, self._model = memory, communication, model

    def respond(self, message: str) -> str:
        profile, history = self._memory.get_user_profile(), self._memory.retrieve_history()
        return self._model.respond(instruction="You are a warm elderly-care companion. Use the supplied Memory MCP context only; do not invent personal facts.", user_message=message, specialist_context=f"Profile: {profile}; Recent history: {history}")

    def contacts(self): return self._communication.get_family_contacts()
    def phone_book(self): return self._communication.get_phone_book()
    def request_family_call(self, contact_query: str): return self._communication.request_family_call(contact_query)
    def send_approved_family_message(self, contact_id: str, content: str, user_approved: bool):
        return self._communication.send_family_message(contact_id, content, user_approved)
