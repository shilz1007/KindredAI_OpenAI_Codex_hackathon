"""OpenAI Realtime WebSocket adapter for the Master Agent voice experience."""

import asyncio
import base64
import json
import struct
import wave
from collections.abc import Callable
from io import BytesIO

import websockets

from kindred_ai.application.ports.realtime_voice import VoiceTurn

REALTIME_SAMPLE_RATE = 24_000


class OpenAIRealtimeVoiceModel:
    """Executes a push-to-talk voice turn over OpenAI's Realtime WebSocket API.

    The model has one narrow tool: consult the Master Agent's approved Guardian
    workflow. The callback is intentionally a Python application boundary, so
    this adapter cannot access MCP clients or databases itself.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        specialist_context: Callable[[str], str],
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._specialist_context = specialist_context

    async def respond_to_wav(self, audio_wav: bytes) -> VoiceTurn:
        """Send a recorded WAV utterance and return Realtime PCM16 speech."""
        pcm16 = wav_to_pcm16(audio_wav)
        url = f"wss://api.openai.com/v1/realtime?model={self._model}"
        # The Realtime API is GA. Do not send the retired `realtime=v1` beta
        # header: GA explicitly rejects beta session/event shapes.
        headers = {"Authorization": f"Bearer {self._api_key}"}
        transcript_parts: list[str] = []
        audio_parts: list[bytes] = []
        completed_responses = 0
        tool_followups = 0

        async with websockets.connect(url, additional_headers=headers) as socket:
            await self._send_session_configuration(socket)
            for chunk in _chunks(pcm16, 24_000):
                await _send_event(socket, "input_audio_buffer.append", audio=base64.b64encode(chunk).decode("ascii"))
            await _send_event(socket, "input_audio_buffer.commit")
            # Require Guardian consultation for the first response to each user
            # utterance. The response created after tool output disables tools
            # so the model can deliver its spoken answer instead of looping.
            await _send_event(socket, "response.create", response={"output_modalities": ["audio"], "tool_choice": "required"})

            async for raw_event in socket:
                event = json.loads(raw_event)
                event_type = event.get("type")
                if event_type == "error":
                    detail = event.get("error", {}).get("message", "Unknown Realtime API error")
                    raise RuntimeError(f"Realtime voice request failed: {detail}")
                if event_type in {"response.audio.delta", "response.output_audio.delta"}:
                    audio_parts.append(base64.b64decode(event["delta"]))
                elif event_type in {"response.audio_transcript.delta", "response.output_audio_transcript.delta"}:
                    transcript_parts.append(event.get("delta", ""))
                elif event_type == "response.function_call_arguments.done":
                    await self._handle_guardian_tool(socket, event)
                    tool_followups += 1
                elif event_type == "response.done":
                    completed_responses += 1
                    # The first response can stop immediately after requesting a
                    # tool. Wait for the response generated from tool output.
                    if completed_responses <= tool_followups:
                        continue
                    transcript = "".join(transcript_parts).strip() or _text_from_response(event)
                    if not audio_parts:
                        raise RuntimeError("Realtime API completed without returning spoken audio.")
                    return VoiceTurn(transcript=transcript, audio_pcm16=b"".join(audio_parts))

        raise RuntimeError("Realtime voice connection closed before a response completed.")

    async def _send_session_configuration(self, socket: websockets.ClientConnection) -> None:
        await _send_event(
            socket,
            "session.update",
            session={
                "type": "realtime",
                "output_modalities": ["audio"],
                "instructions": (
                    "You are Dida, the Kindred AI Master Agent: warm, patient, and clear for older adults. "
                    "For every user request, call consult_guardian before replying. Use its result as fact; "
                    "never invent medicine, orders, or security facts. Speak only in clear English, never Bengali or mixed languages. "
                    "Keep answers concise and speak naturally."
                ),
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": REALTIME_SAMPLE_RATE},
                        "turn_detection": None,
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": REALTIME_SAMPLE_RATE},
                        "voice": "alloy",
                    },
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "consult_guardian",
                        "description": "Consult the approved Guardian workflow before answering the user.",
                        "parameters": {
                            "type": "object",
                            "properties": {"message": {"type": "string", "description": "The user's request."}},
                            "required": ["message"],
                            "additionalProperties": False,
                        },
                    }
                ],
                "tool_choice": "auto",
            },
        )

    async def _handle_guardian_tool(self, socket: websockets.ClientConnection, event: dict[str, object]) -> None:
        if event.get("name") != "consult_guardian":
            raise RuntimeError("Realtime model requested an unapproved tool.")
        try:
            arguments = json.loads(str(event.get("arguments", "{}")))
            message = arguments["message"]
            if not isinstance(message, str) or not message.strip():
                raise ValueError("Tool argument 'message' must be a non-empty string.")
            result = await asyncio.to_thread(self._specialist_context, message)
            output = json.dumps({"specialist_context": result})
        except (json.JSONDecodeError, KeyError, ValueError, RuntimeError) as error:
            output = json.dumps({"error": f"Guardian consultation could not complete: {error}"})
        await _send_event(socket, "conversation.item.create", item={"type": "function_call_output", "call_id": event["call_id"], "output": output})
        await _send_event(socket, "response.create", response={"output_modalities": ["audio"], "tool_choice": "none"})


async def _send_event(socket: websockets.ClientConnection, event_type: str, **payload: object) -> None:
    await socket.send(json.dumps({"type": event_type, **payload}))


def wav_to_pcm16(audio_wav: bytes, target_rate: int = REALTIME_SAMPLE_RATE) -> bytes:
    """Convert a standard mono/stereo signed-16-bit WAV into mono PCM16.

    Gradio records browser audio as WAV. Realtime PCM input is 24 kHz mono, so
    this small dependency-free converter keeps the temporary UI portable.
    """
    with wave.open(BytesIO(audio_wav), "rb") as source:
        channels, width, input_rate = source.getnchannels(), source.getsampwidth(), source.getframerate()
        if source.getcomptype() != "NONE" or width != 2:
            raise ValueError("Voice input must be an uncompressed 16-bit WAV recording.")
        raw = source.readframes(source.getnframes())
    if not raw:
        raise ValueError("Voice input contains no audio.")
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    mono = [sum(samples[index : index + channels]) // channels for index in range(0, len(samples), channels)]
    if input_rate == target_rate:
        return struct.pack(f"<{len(mono)}h", *mono)
    output_length = max(1, round(len(mono) * target_rate / input_rate))
    resampled = [mono[min(len(mono) - 1, round(position * input_rate / target_rate))] for position in range(output_length)]
    return struct.pack(f"<{len(resampled)}h", *resampled)


def pcm16_to_wav(pcm16: bytes, sample_rate: int = REALTIME_SAMPLE_RATE) -> bytes:
    """Wrap returned Realtime PCM16 audio in a browser-playable WAV container."""
    output = BytesIO()
    with wave.open(output, "wb") as destination:
        destination.setnchannels(1)
        destination.setsampwidth(2)
        destination.setframerate(sample_rate)
        destination.writeframes(pcm16)
    return output.getvalue()


def _chunks(value: bytes, size: int):
    for start in range(0, len(value), size):
        yield value[start : start + size]


def _text_from_response(event: dict[str, object]) -> str:
    """Best-effort fallback for Realtime responses without transcript deltas."""
    response = event.get("response", {})
    if not isinstance(response, dict):
        return "Spoken response received."
    status_details = response.get("status_details", {})
    if not isinstance(status_details, dict):
        return "Spoken response received."
    return str(status_details.get("error", "Spoken response received."))
