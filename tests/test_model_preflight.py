import json
import unittest
from unittest.mock import MagicMock, patch

from src.model_preflight import (
    check_lm_studio_model,
    check_mlx_whisper_import,
    check_ollama_model,
    check_streamlit_audio_available,
)


class ModelPreflightTests(unittest.TestCase):
    def test_streamlit_audio_available_when_attribute_exists(self):
        fake_streamlit = MagicMock()
        fake_streamlit.audio_input = object()

        with patch("importlib.import_module", return_value=fake_streamlit):
            result = check_streamlit_audio_available()

        self.assertTrue(result.ready)
        self.assertEqual(result.name, "Streamlit audio input")

    def test_streamlit_audio_unavailable_when_attribute_missing(self):
        fake_streamlit = MagicMock(spec=[])

        with patch("importlib.import_module", return_value=fake_streamlit):
            result = check_streamlit_audio_available()

        self.assertFalse(result.ready)
        self.assertIn("streamlit>=1.40", result.action)

    def test_import_check_reports_missing_mlx_whisper(self):
        with patch("importlib.util.find_spec", return_value=None):
            result = check_mlx_whisper_import()

        self.assertFalse(result.ready)
        self.assertIn("pip install mlx-whisper", result.action)

    def test_import_check_reports_runtime_import_failure(self):
        with (
            patch("importlib.util.find_spec", return_value=object()),
            patch("importlib.import_module", side_effect=RuntimeError("No Metal device available")),
        ):
            result = check_mlx_whisper_import()

        self.assertFalse(result.ready)
        self.assertIn("failed to import", result.message)
        self.assertIn("Metal", result.action)

    def test_ollama_model_check_finds_requested_model(self):
        payload = json.dumps({"models": [{"name": "qwen3:8b"}, {"name": "mistral:7b"}]}).encode()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload

        with patch("urllib.request.urlopen", return_value=response):
            result = check_ollama_model("http://localhost:11434", "qwen3:8b")

        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "ollama")
        self.assertEqual(result.model, "qwen3:8b")

    def test_ollama_model_check_reports_missing_model(self):
        payload = json.dumps({"models": [{"name": "mistral:7b"}]}).encode()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload

        with patch("urllib.request.urlopen", return_value=response):
            result = check_ollama_model("http://localhost:11434", "qwen3:8b")

        self.assertFalse(result.ready)
        self.assertIn("ollama pull qwen3:8b", result.action)

    def test_lm_studio_model_check_finds_requested_model(self):
        payload = json.dumps({"data": [{"id": "local-qwen"}]}).encode()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload

        with patch("urllib.request.urlopen", return_value=response):
            result = check_lm_studio_model("http://localhost:1234/v1", "local-qwen")

        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "lm_studio")
        self.assertEqual(result.model, "local-qwen")


if __name__ == "__main__":
    unittest.main()
