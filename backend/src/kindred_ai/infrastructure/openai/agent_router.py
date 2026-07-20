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

    def __init__(self, *, api_key: str, model: str, instruction: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._instruction = instruction

    def route(self, message: str) -> AgentRoute:
        with observation("llm.agent-router", as_type="generation", input={"message": message}, metadata={"feature": "routing"}) as generation:
            response = self._client.responses.create(
            model=self._model,
            instructions=self._instruction,
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
