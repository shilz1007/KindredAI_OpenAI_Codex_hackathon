"""Optional, privacy-aware Langfuse tracing for Kindred execution paths."""

import os
import re
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Literal

from dotenv import load_dotenv
from langfuse import Langfuse

ENVIRONMENT_FILE = Path(__file__).resolve().parents[3] / ".env"
ObservationType = Literal["agent", "generation", "tool", "span", "retriever"]


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    """Create a client only when the user has configured Langfuse keys."""
    load_dotenv(ENVIRONMENT_FILE)
    if os.getenv("KINDRED_DISABLE_LLM", "false").lower() == "true":
        # Offline/unit-test mode must not emit external telemetry.
        return None
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        return None
    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        base_url=os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST"),
        environment=os.getenv("KINDRED_ENVIRONMENT", "development"),
    )


def safe_value(value: Any) -> Any:
    """Keep traces useful while redacting phone-number-like values and bounding size."""
    if isinstance(value, str):
        cleaned = re.sub(r"\+?\d[\d\s()-]{7,}\d", "[redacted phone]", value)
        return cleaned[:1_000]
    if isinstance(value, dict):
        return {str(key): safe_value(item) for key, item in value.items() if "key" not in str(key).lower() and "secret" not in str(key).lower()}
    if isinstance(value, (list, tuple)):
        return [safe_value(item) for item in value[:20]]
    return value


@contextmanager
def observation(name: str, *, as_type: ObservationType = "span", input: Any = None, metadata: dict[str, Any] | None = None) -> Iterator[Any | None]:
    """Create a nested observation when Langfuse is configured; otherwise no-op."""
    client = get_langfuse_client()
    if client is None:
        yield None
        return
    with client.start_as_current_observation(name=name, as_type=as_type, input=safe_value(input), metadata=safe_value(metadata or {})) as current:
        try:
            yield current
        except Exception as error:
            current.update(level="ERROR", status_message=str(error)[:500])
            raise


def record_output(current: Any | None, output: Any, *, model: str | None = None, usage: dict[str, int] | None = None) -> None:
    if current is not None:
        current.update(output=safe_value(output), model=model, usage_details=usage)
