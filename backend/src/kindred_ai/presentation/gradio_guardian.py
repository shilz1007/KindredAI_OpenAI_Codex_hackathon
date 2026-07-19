"""Temporary Gradio interface for manually testing Master-to-Guardian workflows.

This is a development-only test harness, not the Kindred AI product UI.
"""

import asyncio
import tempfile
from uuid import uuid4
from pathlib import Path

import gradio as gr

from kindred_ai.application.master import get_master_agent
from kindred_ai.application.master_voice import get_master_voice_model
from kindred_ai.infrastructure.openai.realtime_voice import pcm16_to_wav


def master_reply(message: str, *, session_id: str = "default") -> str:
    """Send a user message through Master Agent and its Guardian delegation.

    Supported test phrases:
    - Any safety/fraud-style message: Master routes it to Guardian and receives Security MCP context.
    - "show medication supply": displays calculated days remaining.
    - "confirm order <medicine> <quantity>": creates a confirmed refill request.
    """
    cleaned = message.strip()
    if not cleaned:
        return "Please enter a message to test Guardian Agent."

    try:
        return get_master_agent().respond(cleaned, session_id=session_id)
    except (RuntimeError, ValueError) as error:
        return f"The Master test UI could not complete the request: {error}"


def master_voice_reply(audio_path: str | None) -> tuple[str, str | None]:
    """Send a push-to-talk microphone recording through the Realtime Master."""
    if not audio_path:
        return "Please record a voice message before sending it.", None
    try:
        voice_turn = asyncio.run(get_master_voice_model().respond_to_wav(Path(audio_path).read_bytes()))
        with tempfile.NamedTemporaryFile(prefix="kindred-reply-", suffix=".wav", delete=False) as output:
            output.write(pcm16_to_wav(voice_turn.audio_pcm16, voice_turn.sample_rate))
        return voice_turn.transcript or "Spoken response received.", output.name
    except Exception as error:  # The temporary UI should show network/API failures rather than a Gradio traceback.
        return f"The Realtime voice test could not complete: {error}", None


def build_demo() -> gr.Blocks:
    """Build the local-only Guardian Agent test interface."""
    with gr.Blocks(title="Kindred AI — Guardian Test UI") as demo:
        gr.Markdown(
            "# Master Agent Test UI\n"
            "Temporary development harness. The text panel uses the Responses API; the voice panel sends microphone WAV audio "
            "to the OpenAI Realtime WebSocket API and plays the spoken reply. Try a suspicious message, `show medication supply`, "
            "or `confirm order Metformin 60`."
        )
        chat = gr.Chatbot(label="Master Agent")
        message = gr.Textbox(label="Test message", placeholder="Urgent: send your gift card details now.")
        clear = gr.Button("Clear")
        session = gr.State(value=str(uuid4()))

        def respond(user_message: str, history: list[dict[str, str]], session_id: str) -> tuple[str, list[dict[str, str]]]:
            reply = master_reply(user_message, session_id=session_id)
            return "", [*history, {"role": "user", "content": user_message}, {"role": "assistant", "content": reply}]

        def clear_chat(session_id: str) -> tuple[list[dict[str, str]], str]:
            get_master_agent().clear_conversation(session_id)
            return [], str(uuid4())

        message.submit(respond, inputs=[message, chat, session], outputs=[message, chat])
        clear.click(clear_chat, inputs=session, outputs=[chat, session])

        gr.Markdown("## Realtime voice test\nRecord a short message, then select **Send voice message**. This is push-to-talk; continuous streaming is a later UI enhancement.")
        microphone = gr.Audio(label="Microphone", sources=["microphone"], type="filepath", format="wav")
        send_voice = gr.Button("Send voice message")
        clear_voice = gr.Button("Clear voice test")
        voice_transcript = gr.Textbox(label="Assistant transcript", interactive=False)
        voice_audio = gr.Audio(label="Dida's spoken reply", type="filepath", autoplay=True)
        send_voice.click(master_voice_reply, inputs=microphone, outputs=[voice_transcript, voice_audio])
        clear_voice.click(lambda: (None, "", None), outputs=[microphone, voice_transcript, voice_audio])
    return demo


if __name__ == "__main__":
    build_demo().launch()
