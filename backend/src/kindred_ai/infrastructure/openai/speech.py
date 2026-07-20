"""OpenAI-backed speech output for the browser Care Hub."""

from openai import OpenAI

from kindred_ai.infrastructure.observability import observation, record_output


class OpenAISpeechService:
    """Generate one consistent, English-only Kindred speaking voice."""

    def __init__(self, *, api_key: str, model: str, voice: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._voice = voice

    def synthesize(self, text: str) -> bytes:
        """Return browser-playable WAV audio for a short Master reply.

        WAV avoids the MP3 encoder-delay behaviour that clipped the first words
        of some spoken replies in browser playback.
        """
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Speech text cannot be empty.")
        if len(clean_text) > 4_000:
            raise ValueError("Speech text is too long.")

        with observation(
            "llm.speech",
            as_type="generation",
            input={"characters": len(clean_text)},
            metadata={"feature": "care-hub-speech", "voice": self._voice},
        ) as generation:
            response = self._client.audio.speech.create(
                model=self._model,
                voice=self._voice,
                input=clean_text,
                response_format="wav",
            )
            audio = response.read()
            record_output(generation, {"audio_bytes": len(audio)}, model=self._model)
            return audio
