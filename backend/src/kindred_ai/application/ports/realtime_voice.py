"""Port for an audio-in/audio-out Master conversation turn."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VoiceTurn:
    """Spoken response data returned by a Realtime provider."""

    transcript: str
    audio_pcm16: bytes
    sample_rate: int = 24_000


class RealtimeVoiceModel(Protocol):
    """Keeps Realtime provider details out of presentation and agent layers."""

    async def respond_to_wav(self, audio_wav: bytes) -> VoiceTurn:
        """Accept one microphone WAV recording and return one spoken answer."""
