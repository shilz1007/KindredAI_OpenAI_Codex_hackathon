"""Tests for local audio conversion used by the Realtime voice adapter."""

import struct
import unittest
import wave
from io import BytesIO

from kindred_ai.infrastructure.openai.realtime_voice import pcm16_to_wav, wav_to_pcm16


class RealtimeVoiceTests(unittest.TestCase):
    def test_wav_input_is_converted_to_realtime_pcm_and_wrapped_for_playback(self) -> None:
        source = BytesIO()
        with wave.open(source, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48_000)
            wav.writeframes(struct.pack("<4h", 100, -100, 200, -200))

        pcm = wav_to_pcm16(source.getvalue())
        playable = pcm16_to_wav(pcm)

        with wave.open(BytesIO(playable), "rb") as wav:
            self.assertEqual(wav.getframerate(), 24_000)
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertGreater(wav.getnframes(), 0)

    def test_empty_wav_is_rejected(self) -> None:
        source = BytesIO()
        with wave.open(source, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24_000)
            wav.writeframes(b"")

        with self.assertRaisesRegex(ValueError, "contains no audio"):
            wav_to_pcm16(source.getvalue())
