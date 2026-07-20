"""OpenAI Responses adapter for Tavily's hosted, read-only remote MCP server."""

import json
import re
from urllib.parse import quote

from openai import OpenAI

from kindred_ai.infrastructure.observability import observation, record_output


class TavilyResearchError(RuntimeError):
    """Raised when a live public-information lookup cannot complete."""


class UnavailableResearchModel:
    """Safe fallback used when an optional Tavily deployment key is absent."""

    def research(self, *, query: str, instruction: str) -> str:
        raise TavilyResearchError("Live research is not configured right now.")


class TavilyResearchModel:
    """Uses the Responses API remote-MCP tool without exposing Tavily credentials."""

    def __init__(self, *, api_key: str, tavily_api_key: str, model: str, client: OpenAI | None = None) -> None:
        if not tavily_api_key.strip():
            raise TavilyResearchError("Live research is unavailable because Tavily is not configured.")
        self._client = client or OpenAI(api_key=api_key)
        self._model = model
        self._server_url = "https://mcp.tavily.com/mcp/?tavilyApiKey=" + quote(tavily_api_key, safe="")

    def research(self, *, query: str, instruction: str) -> str:
        with observation("llm.tavily-research", as_type="generation", input={"query": query}, metadata={"feature": "live-research", "provider": "tavily"}) as generation:
            try:
                response = self._client.responses.create(
                    model=self._model,
                    instructions=instruction,
                    input=query,
                    tools=[
                        {
                            "type": "mcp",
                            "server_label": "tavily",
                            "server_url": self._server_url,
                            "require_approval": "never",
                            "headers": {
                                "DEFAULT_PARAMETERS": json.dumps(
                                    {
                                        "include_favicon": True,
                                        "include_images": False,
                                        "include_raw_content": False,
                                    }
                                )
                            },
                        }
                    ],
                )
            except Exception as error:
                raise TavilyResearchError("I could not complete a live search right now. Please try again shortly.") from error
            answer = _plain_english_text(response.output_text)
            if not answer:
                raise TavilyResearchError("I could not find a clear live answer right now. Please try again shortly.")
            usage = getattr(response, "usage", None)
            record_output(generation, {"answer": answer}, model=self._model, usage=usage.model_dump() if usage else None)
            return answer


def _plain_english_text(value: str) -> str:
    """Remove presentation markup before a Research answer is spoken aloud."""
    cleaned = value.strip().replace("**", "").replace("__", "")
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()
