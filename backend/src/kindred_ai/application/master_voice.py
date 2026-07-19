"""Factory for the Master Agent's Realtime voice adapter."""

from functools import lru_cache

from kindred_ai.application.master import get_master_agent
from kindred_ai.config.model_settings import get_model_settings
from kindred_ai.infrastructure.openai.realtime_voice import OpenAIRealtimeVoiceModel


@lru_cache(maxsize=1)
def get_master_voice_model() -> OpenAIRealtimeVoiceModel:
    """Create the voice adapter with only Master-approved delegation access."""
    master = get_master_agent()
    settings = get_model_settings()
    return OpenAIRealtimeVoiceModel(
        api_key=settings.api_key,
        model=settings.master_model,
        specialist_context=master.get_specialist_context,
    )
