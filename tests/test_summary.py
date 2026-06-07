import json
import unittest

from src.review import apply_review_action, initialize_review_items
from src.summary import (
    final_summary_to_json,
    final_summary_to_markdown,
    generate_final_summary,
)


class SummaryTests(unittest.TestCase):
    def test_final_summary_uses_human_approved_glossary_and_model_metadata(self):
        review_items = initialize_review_items(
            [
                {
                    "term": "GTM",
                    "canonical": "Go-to-Market",
                    "explanation": "The plan for bringing a product to customers.",
                    "source": "dictionary,llm",
                    "confidence": 0.93,
                },
                {
                    "term": "ARR",
                    "canonical": "Annual Recurring Revenue",
                    "explanation": "Revenue expected from subscriptions over a year.",
                    "source": "dictionary,llm",
                    "confidence": 0.95,
                },
                {
                    "term": "motion",
                    "canonical": "Motion",
                    "explanation": "A strategy or operating approach for doing business.",
                    "source": "heuristic",
                    "confidence": 0.60,
                },
            ],
            model="qwen3:8b",
        )
        audit = []
        apply_review_action(review_items, audit, "GTM", "approve", timestamp="2026-06-07T12:00:00Z")
        apply_review_action(
            review_items,
            audit,
            "ARR",
            "edit",
            edited_text="The predictable subscription revenue the business expects each year.",
            timestamp="2026-06-07T12:01:00Z",
        )
        apply_review_action(review_items, audit, "motion", "reject", timestamp="2026-06-07T12:02:00Z")

        summary = generate_final_summary(
            transcript="Let's revisit our GTM motion before Q3 and improve ARR.",
            simplifications={
                "simple": "Review the sales plan before Q3 and improve yearly subscription revenue.",
                "professional": "Revisit the go-to-market plan before Q3 and improve ARR.",
                "expert": "Refine GTM execution before Q3 and expand ARR.",
            },
            action_items=["Revisit the go-to-market plan before Q3."],
            review_items=review_items,
            review_audit=audit,
            asr_status={"provider": "mlx_whisper", "model": "mlx-community/whisper-large-v3-turbo"},
            llm_status={"provider": "ollama", "model": "qwen3:8b"},
        )

        glossary_terms = {entry["term"]: entry for entry in summary["human_approved_glossary"]}

        self.assertEqual(summary["plain_english_summary"], "Review the sales plan before Q3 and improve yearly subscription revenue.")
        self.assertEqual(glossary_terms["ARR"]["explanation"], "The predictable subscription revenue the business expects each year.")
        self.assertIn("GTM", glossary_terms)
        self.assertNotIn("motion", glossary_terms)
        self.assertEqual(summary["model_metadata"]["asr"]["provider"], "mlx_whisper")
        self.assertEqual(summary["model_metadata"]["llm"]["model"], "qwen3:8b")
        self.assertEqual(summary["review_audit"], audit)

    def test_json_and_markdown_exports_include_reviewed_output(self):
        summary = {
            "plain_english_summary": "Plain output.",
            "key_terms": [{"term": "ARR", "canonical": "Annual Recurring Revenue"}],
            "action_items": ["Improve ARR."],
            "human_approved_glossary": [
                {
                    "term": "ARR",
                    "canonical": "Annual Recurring Revenue",
                    "explanation": "The predictable subscription revenue the business expects each year.",
                }
            ],
            "model_metadata": {
                "asr": {"provider": "mlx_whisper", "model": "mlx-community/whisper-large-v3-turbo"},
                "llm": {"provider": "ollama", "model": "qwen3:8b"},
            },
            "review_audit": [],
        }

        parsed = json.loads(final_summary_to_json(summary))
        markdown = final_summary_to_markdown(summary)

        self.assertEqual(parsed["plain_english_summary"], "Plain output.")
        self.assertIn("The predictable subscription revenue", markdown)
        self.assertIn("ollama qwen3:8b", markdown)


if __name__ == "__main__":
    unittest.main()
