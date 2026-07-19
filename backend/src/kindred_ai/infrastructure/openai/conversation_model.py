"""OpenAI Responses API adapter for text conversation and specialist guidance."""

from openai import OpenAI

from kindred_ai.application.ports.conversation_model import ConversationModel
from kindred_ai.infrastructure.observability import observation, record_output


class OpenAIConversationModel(ConversationModel):
    """Calls the configured Master model; tool decisions remain in Python."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def respond(self, *, instruction: str, user_message: str, specialist_context: str) -> str:
        with observation("llm.conversation-response", as_type="generation", input={"user_message": user_message, "specialist_context": specialist_context}, metadata={"feature": "conversation"}) as generation:
            response = self._client.responses.create(
            model=self._model,
            instructions=instruction,
            input=f"User message:\n{user_message}\n\nSpecialist result:\n{specialist_context}",
            )
            output = response.output_text.strip()
            usage = getattr(response, "usage", None)
            record_output(generation, {"reply": output}, model=self._model, usage=usage.model_dump() if usage else None)
            return output
