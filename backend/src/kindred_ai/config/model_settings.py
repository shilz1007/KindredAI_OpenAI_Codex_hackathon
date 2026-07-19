"""Local model configuration loaded from the ignored backend/.env file."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENVIRONMENT_FILE = Path(__file__).resolve().parents[3] / ".env"


@dataclass(frozen=True, slots=True)
class ModelSettings:
    api_key: str
    master_model: str
    agents_model: str


def get_model_settings() -> ModelSettings:
    """Load required local OpenAI configuration without exposing secret values."""
    load_dotenv(ENVIRONMENT_FILE)
    api_key = os.getenv("OPENAI_API_KEY")
    master_model = os.getenv("OPENAI_MODEL_MASTER")
    agents_model = os.getenv("OPENAI_MODEL_AGENTS")
    missing = [name for name, value in (("OPENAI_API_KEY", api_key), ("OPENAI_MODEL_MASTER", master_model), ("OPENAI_MODEL_AGENTS", agents_model)) if not value]
    if missing:
        raise RuntimeError(f"Missing required local model configuration: {', '.join(missing)}.")
    return ModelSettings(api_key=api_key, master_model=master_model, agents_model=agents_model)
