import sys
import types
import unittest
from unittest.mock import patch

from src.transcription import transcribe_audio, transcribe_with_faster_whisper, transcribe_with_mlx


class FakeSegment:
    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text


class FakeInfo:
    language = "en"


class TranscriptionTests(unittest.TestCase):
    def test_mlx_transcription_returns_structured_result(self):
        fake_mlx = types.SimpleNamespace(
            transcribe=lambda path, path_or_hf_repo: {
                "text": " Hello world ",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Hello world"}],
                "language": "en",
            }
        )

        with patch.dict(sys.modules, {"mlx_whisper": fake_mlx}):
            result = transcribe_with_mlx("/tmp/audio.wav", "test-model")

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "mlx_whisper")
        self.assertEqual(result["model"], "test-model")
        self.assertEqual(result["text"], "Hello world")
        self.assertEqual(result["language"], "en")

    def test_faster_whisper_transcription_returns_structured_result(self):
        class FakeWhisperModel:
            def __init__(self, model_size, device, compute_type):
                self.model_size = model_size
                self.device = device
                self.compute_type = compute_type

            def transcribe(self, path, beam_size, vad_filter):
                return [FakeSegment(0.0, 0.5, "Hello"), FakeSegment(0.5, 1.0, "world")], FakeInfo()

        fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)

        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            result = transcribe_with_faster_whisper("/tmp/audio.wav", "base.en")

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "faster_whisper")
        self.assertEqual(result["model"], "base.en")
        self.assertEqual(result["text"], "Hello world")
        self.assertEqual(result["segments"][0]["start"], 0.0)

    def test_auto_provider_falls_back_to_real_backup(self):
        mlx_failure = {
            "ok": False,
            "provider": "mlx_whisper",
            "model": "mlx-model",
            "text": "",
            "segments": [],
            "language": None,
            "error": "mlx unavailable",
            "fallback_errors": [],
        }
        faster_success = {
            "ok": True,
            "provider": "faster_whisper",
            "model": "small.en",
            "text": "backup transcript",
            "segments": [],
            "language": "en",
            "error": None,
            "fallback_errors": [],
        }

        with (
            patch("src.transcription.transcribe_with_mlx", return_value=mlx_failure),
            patch("src.transcription.transcribe_with_faster_whisper", return_value=faster_success),
        ):
            result = transcribe_audio("/tmp/audio.wav", provider="auto", mlx_model="mlx-model")

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "faster_whisper")
        self.assertEqual(result["fallback_errors"], ["mlx unavailable"])

    def test_provider_failure_does_not_create_fake_transcript(self):
        result = transcribe_audio("/tmp/audio.wav", provider="unknown")  # type: ignore[arg-type]

        self.assertFalse(result["ok"])
        self.assertEqual(result["text"], "")
        self.assertIn("Unsupported ASR provider", result["error"])


if __name__ == "__main__":
    unittest.main()
