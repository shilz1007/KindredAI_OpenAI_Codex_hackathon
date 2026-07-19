"""OpenAI structured-output implementation of Master intent routing."""

from openai import OpenAI

from kindred_ai.application.ports.agent_router import AgentRoute
from kindred_ai.infrastructure.observability import observation, record_output


def _strict_route_schema() -> dict:
    """Adapt Pydantic's optional-field schema to OpenAI strict JSON Schema.

    OpenAI requires every declared property to be listed as required; optional
    route values are represented by an explicit JSON ``null`` instead.
    """
    schema = AgentRoute.model_json_schema()
    schema["required"] = list(schema["properties"])
    for property_schema in schema["properties"].values():
        property_schema.pop("default", None)
    return schema


class OpenAIAgentRouter:
    """Returns a validated route; execution remains in the Master Agent."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def route(self, message: str) -> AgentRoute:
        with observation("llm.agent-router", as_type="generation", input={"message": message}, metadata={"feature": "routing"}) as generation:
            response = self._client.responses.create(
            model=self._model,
            instructions=(
                "Classify the user's request for Kindred AI. Return only the requested schema. "
                "Master handles general safety/cybersecurity advice without inspecting any stored messages. "
                "Use Guardian's security_inbox intent only when the user explicitly asks to read, check, or list phone messages that were already received or stored in Kindred, including questions such as 'Do I have new messages?' or 'Read my phone messages'. "
                "A general question such as whether it is safe to share a code stays with Master as general_safety_guidance. Guardian handles medication supply and medication replenishment. "
                "Companion handles social conversation, memory, and requests to call an approved family member. "
                "Use communication_call and extract contact_query for a call request. Logistics handles non-medication household stock, purchase requests, and reminders. "
                "Use household_inventory, household_purchase, or household_reminder for those specific Logistics requests. "
                "Do not claim a purchase is authorized. Extract medication or household item names and quantity only when clearly stated. "
                "For a household reminder, extract reminder_title and an ISO 8601 time with timezone only when the user clearly provides one."
            ),
            input=message,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "agent_route",
                    "strict": True,
                    "schema": _strict_route_schema(),
                }
            },
            )
            route = AgentRoute.model_validate_json(response.output_text)
            usage = getattr(response, "usage", None)
            record_output(generation, route.model_dump(), model=self._model, usage=usage.model_dump() if usage else None)
            return route
