import os
import json
import asyncio
import logging
from dotenv import load_dotenv
import websockets

# Configure logging to clearly see the real-time event pipeline in action
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("RealtimeClient")

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-realtime-1.5"
WS_URL = f"wss://api.openai.com/v1/realtime?model={MODEL_NAME}"

if not OPENAI_API_KEY:
    logger.error("❌ OPENAI_API_KEY is not defined in your environment variables. Please add it to your .env file.")

async def run_realtime_connection():
    """
    Connects to the OpenAI Realtime API using gpt-realtime-1.5,
    performs the handshake, updates the session guidelines,
    and listens to incoming text and audio stream events.
    """
    # Configure headers required by the OpenAI Realtime WebSocket protocol
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    logger.info(f"🔗 Attempting connection to OpenAI Realtime API at: {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL, additional_headers=headers) as ws:
            logger.info("✅ Connection established successfully!")

            # Immediately send a session.update event to configure the agent's identity
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": (
                        "You are 'Dida', a warm, patient Bengali-English bilingual "
                        "companion for elderly users. Answer clearly, slowly, and warmly."
                    ),
                    "voice": "alloy",
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "turn_detection": {
                        "type": "server_vad"
                    }
                }
            }
            
            logger.info("📤 Sending initial session.update configuration to guide the model...")
            await ws.send(json.dumps(session_config))

            async def send_ping_loop():
                """Simulates ambient ping frames to maintain a active connection state."""
                try:
                    while True:
                        await asyncio.sleep(15)
                        # We can send raw audio or message triggers here
                        # For an isolated demo, we'll log heartbeat events
                        logger.debug("💓 Heartbeat ping keeping connection alive.")
                except asyncio.CancelledError:
                    pass

            async def receive_events_loop():
                """Main loop for listening and parsing events coming from gpt-realtime-1.5."""
                try:
                    async for raw_message in ws:
                        event = json.loads(raw_message)
                        event_type = event.get("type")
                        
                        if event_type == "session.updated":
                            logger.info("✨ Session configuration updated successfully on OpenAI server!")
                        elif event_type == "response.audio_transcript.delta":
                            # Stream the real-time text transcription as it's generated
                            print(event.get("delta"), end="", flush=True)
                        elif event_type == "response.done":
                            print("\n") # New line after stream ends
                            logger.info("🏁 Response generation completed.")
                        elif event_type == "error":
                            logger.error(f"🚨 OpenAI Realtime Error: {event.get('error')}")
                        else:
                            # Log ambient trace events to understand internal processing state
                            logger.debug(f"Received event: {event_type}")
                except Exception as e:
                    logger.error(f"Exception in event listener: {e}")

            # Run parallel stream loops concurrently
            await asyncio.gather(
                send_ping_loop(),
                receive_events_loop()
            )

    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"🔌 Connection closed by server: Code {e.code}, Reason: {e.reason}")
    except Exception as e:
        logger.error(f"🚨 Connection failed: {e}")

if __name__ == "__main__":
    if OPENAI_API_KEY:
        try:
            asyncio.run(run_realtime_connection())
        except KeyboardInterrupt:
            logger.info("\n🛑 Client shut down by user.")