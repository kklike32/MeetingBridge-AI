import json
import unittest
from unittest.mock import MagicMock, patch

from src.llm_client import (
    LLMClientError,
    LLMConfig,
    build_meeting_intelligence_prompt,
    extract_json_object,
    generate_meeting_intelligence,
    strip_thinking_blocks,
    validate_meeting_intelligence_payload,
)
from src.model_preflight import PreflightResult


VALID_PAYLOAD = {
    "simplifications": {
        "simple": "Use the product to grow revenue and lose fewer customers.",
        "professional": "Improve go-to-market performance before Q3.",
        "expert": "Optimize GTM execution, ARR expansion, and enterprise churn reduction.",
    },
    "glossary": [
        {
            "term": "GTM",
            "canonical": "Go-to-Market",
            "explanation": "The plan for bringing a product to customers.",
            "confidence": 0.91,
            "needs_review": False,
        }
    ],
    "action_items": ["Revisit the go-to-market plan before Q3."],
}


class LLMClientTests(unittest.TestCase):
    def test_prompt_uses_no_think_and_json_schema(self):
        system_prompt, user_prompt = build_meeting_intelligence_prompt(
            "Improve ARR.",
            [{"term": "ARR", "canonical": "Annual Recurring Revenue"}],
        )

        self.assertIn("/no_think", system_prompt)
        self.assertIn("Return only JSON", user_prompt)
        self.assertIn("simplifications", user_prompt)
        self.assertIn("Annual Recurring Revenue", user_prompt)

    def test_strip_thinking_blocks_removes_qwen_thoughts(self):
        text = "<think>private reasoning</think>{\"ok\": true}"

        self.assertEqual(strip_thinking_blocks(text), "{\"ok\": true}")

    def test_extract_json_object_accepts_surrounding_prose(self):
        payload = extract_json_object("Here is JSON:\n" + json.dumps(VALID_PAYLOAD))

        self.assertEqual(payload["simplifications"]["simple"], VALID_PAYLOAD["simplifications"]["simple"])

    def test_validate_payload_clamps_confidence_and_preserves_required_shape(self):
        payload = dict(VALID_PAYLOAD)
        payload["glossary"] = [dict(VALID_PAYLOAD["glossary"][0], confidence=4)]

        normalized = validate_meeting_intelligence_payload(payload)

        self.assertEqual(normalized["glossary"][0]["confidence"], 1.0)
        self.assertEqual(normalized["action_items"], VALID_PAYLOAD["action_items"])

    def test_generate_retries_once_after_malformed_json(self):
        config = LLMConfig(provider="ollama", model="qwen3:8b", base_url="http://localhost:11434")
        ready = PreflightResult(
            name="Ollama model",
            ready=True,
            message="ready",
            provider="ollama",
            model="qwen3:8b",
        )

        with (
            patch("src.llm_client.check_ollama_model", return_value=ready),
            patch("src.llm_client.call_ollama", side_effect=["not json", json.dumps(VALID_PAYLOAD)]) as call,
        ):
            result = generate_meeting_intelligence("Improve ARR.", [], config)

        self.assertEqual(call.call_count, 2)
        self.assertEqual(result["provider"], "ollama")
        self.assertEqual(result["model"], "qwen3:8b")
        self.assertEqual(result["simplifications"]["simple"], VALID_PAYLOAD["simplifications"]["simple"])

    def test_generate_raises_readiness_error_without_fake_output(self):
        config = LLMConfig(provider="ollama", model="qwen3:8b", base_url="http://localhost:11434")
        not_ready = PreflightResult(
            name="Ollama model",
            ready=False,
            message="Ollama is not reachable.",
            action="ollama serve\nollama pull qwen3:8b",
            provider="ollama",
            model="qwen3:8b",
        )

        with patch("src.llm_client.check_ollama_model", return_value=not_ready):
            with self.assertRaises(LLMClientError) as context:
                generate_meeting_intelligence("Improve ARR.", [], config)

        self.assertIn("Ollama is not reachable", str(context.exception))
        self.assertIn("ollama pull qwen3:8b", context.exception.action)

    def test_lm_studio_uses_real_chat_completion_endpoint(self):
        config = LLMConfig(provider="lm_studio", model="local-model", base_url="http://localhost:1234/v1")
        ready = PreflightResult(
            name="LM Studio model",
            ready=True,
            message="ready",
            provider="lm_studio",
            model="local-model",
        )

        with (
            patch("src.llm_client.check_lm_studio_model", return_value=ready),
            patch("src.llm_client.call_lm_studio", return_value=json.dumps(VALID_PAYLOAD)) as call,
        ):
            result = generate_meeting_intelligence("Improve ARR.", [], config)

        self.assertEqual(call.call_count, 1)
        self.assertEqual(result["provider"], "lm_studio")
        self.assertEqual(result["model"], "local-model")


if __name__ == "__main__":
    unittest.main()
