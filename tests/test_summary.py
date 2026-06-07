import json
import unittest

from src.review import apply_review_action, initialize_review_items
from src.summary import (
    build_participant_accessibility_view,
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
        self.assertEqual(
            summary["review_progress"],
            {"pending": 0, "approved": 1, "edited": 1, "rejected": 1, "total": 3},
        )

    def test_json_and_markdown_exports_include_reviewed_output(self):
        summary = {
            "transcript": "Corrected transcript text.",
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
            "review_audit": [
                {
                    "timestamp": "2026-06-07T12:00:00Z",
                    "term": "ARR",
                    "action": "edit",
                    "before": "Old explanation.",
                    "after": "New explanation.",
                    "source_model": "qwen3:8b",
                }
            ],
        }

        parsed = json.loads(final_summary_to_json(summary))
        markdown = final_summary_to_markdown(summary)

        self.assertEqual(parsed["plain_english_summary"], "Plain output.")
        self.assertIn("Corrected transcript text.", markdown)
        self.assertIn("The predictable subscription revenue", markdown)
        self.assertIn("ollama qwen3:8b", markdown)
        self.assertIn("## Review Audit", markdown)
        self.assertIn("ARR: edit", markdown)

    def test_participant_accessibility_view_groups_plain_language_output_and_risk_flags(self):
        summary = {
            "transcript": "Corrected transcript text.",
            "plain_english_summary": "Plain output.",
            "action_items": ["Improve ARR."],
            "human_approved_glossary": [
                {
                    "term": "ARR",
                    "canonical": "Annual Recurring Revenue",
                    "explanation": "The predictable subscription revenue the business expects each year.",
                    "status": "edited",
                }
            ],
            "needs_review": [{"term": "GTM", "canonical": "Go-to-Market", "status": "pending"}],
            "review_progress": {"pending": 1, "approved": 0, "edited": 1, "rejected": 1, "total": 3},
        }

        participant_view = build_participant_accessibility_view(
            summary,
            transcript_raw="Raw ASR transcript text.",
        )

        self.assertEqual(participant_view["sections"]["what_was_said"], "Corrected transcript text.")
        self.assertEqual(participant_view["sections"]["what_it_means"], "Plain output.")
        self.assertEqual(participant_view["sections"]["what_i_need_to_do_next"], ["Improve ARR."])
        self.assertEqual(participant_view["sections"]["terms_i_may_not_know"][0]["term"], "ARR")
        self.assertTrue(participant_view["understanding_checklist"]["transcript_reviewed"])
        self.assertFalse(participant_view["understanding_checklist"]["glossary_terms_reviewed"])
        self.assertTrue(participant_view["understanding_checklist"]["action_items_confirmed"])
        self.assertFalse(participant_view["understanding_checklist"]["final_notes_ready"])
        self.assertEqual(participant_view["risk_flags"]["pending_review_terms"]["count"], 1)
        self.assertEqual(participant_view["risk_flags"]["rejected_terms_excluded"]["count"], 1)
        self.assertEqual(participant_view["risk_flags"]["edited_explanations_used"]["count"], 1)
        self.assertTrue(participant_view["risk_flags"]["transcript_corrected_after_asr"]["active"])
        self.assertFalse(participant_view["risk_flags"]["missing_or_unconfirmed_action_items"]["active"])

    def test_markdown_export_includes_participant_accessibility_view_when_present(self):
        summary = {
            "transcript": "Corrected transcript text.",
            "plain_english_summary": "Plain output.",
            "key_terms": [],
            "action_items": [],
            "human_approved_glossary": [],
            "participant_accessibility_view": {
                "sections": {
                    "what_was_said": "Corrected transcript text.",
                    "what_it_means": "Plain output.",
                    "terms_i_may_not_know": [],
                    "what_i_need_to_do_next": [],
                },
                "understanding_checklist": {
                    "transcript_reviewed": True,
                    "glossary_terms_reviewed": True,
                    "action_items_confirmed": False,
                    "final_notes_ready": False,
                },
                "risk_flags": {
                    "missing_or_unconfirmed_action_items": {
                        "active": True,
                        "label": "Missing or unconfirmed action items",
                        "details": "No confirmed action items are included.",
                    }
                },
            },
            "model_metadata": {"asr": {}, "llm": {}},
            "review_audit": [],
        }

        markdown = final_summary_to_markdown(summary)

        self.assertIn("## Participant Mode / Accessibility View", markdown)
        self.assertIn("### What was said", markdown)
        self.assertIn("- [x] Transcript reviewed", markdown)
        self.assertIn("- [ ] Action items confirmed", markdown)
        self.assertIn("Missing or unconfirmed action items", markdown)


if __name__ == "__main__":
    unittest.main()
