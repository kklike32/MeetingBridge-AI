import unittest

from src.review import (
    apply_review_action,
    approved_glossary_from_review,
    initialize_review_items,
    review_gate_status,
    review_progress,
)


DETECTED_TERMS = [
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
]


class ReviewTests(unittest.TestCase):
    def test_initialize_review_items_creates_pending_items_with_model_metadata(self):
        items = initialize_review_items(DETECTED_TERMS, model="qwen3:8b")

        self.assertEqual(items["GTM"]["status"], "pending")
        self.assertEqual(items["GTM"]["current_explanation"], DETECTED_TERMS[0]["explanation"])
        self.assertEqual(items["GTM"]["model"], "qwen3:8b")

    def test_apply_actions_records_audit_and_approved_glossary_excludes_rejected_terms(self):
        items = initialize_review_items(DETECTED_TERMS, model="qwen3:8b")
        audit = []

        apply_review_action(items, audit, "GTM", "approve", timestamp="2026-06-07T12:00:00Z")
        apply_review_action(
            items,
            audit,
            "ARR",
            "edit",
            edited_text="  The predictable subscription revenue the business expects each year.  ",
            timestamp="2026-06-07T12:01:00Z",
        )
        apply_review_action(items, audit, "motion", "reject", timestamp="2026-06-07T12:02:00Z")

        glossary = approved_glossary_from_review(items)

        self.assertEqual(items["ARR"]["status"], "edited")
        self.assertEqual(
            glossary["ARR"]["explanation"],
            "The predictable subscription revenue the business expects each year.",
        )
        self.assertIn("GTM", glossary)
        self.assertNotIn("motion", glossary)
        self.assertEqual([entry["action"] for entry in audit], ["approve", "edit", "reject"])
        self.assertEqual(audit[1]["before"], "Revenue expected from subscriptions over a year.")
        self.assertEqual(audit[1]["after"], "The predictable subscription revenue the business expects each year.")

    def test_empty_edit_is_rejected_without_audit_entry(self):
        items = initialize_review_items(DETECTED_TERMS, model="qwen3:8b")
        audit = []

        with self.assertRaises(ValueError):
            apply_review_action(items, audit, "ARR", "edit", edited_text="   ")

        self.assertEqual(items["ARR"]["status"], "pending")
        self.assertEqual(audit, [])

    def test_review_progress_counts_statuses(self):
        items = initialize_review_items(DETECTED_TERMS, model="qwen3:8b")
        audit = []
        apply_review_action(items, audit, "GTM", "approve")
        apply_review_action(items, audit, "motion", "reject")

        self.assertEqual(
            review_progress(items),
            {"pending": 1, "approved": 1, "edited": 0, "rejected": 1, "total": 3},
        )

    def test_review_gate_requires_every_item_to_be_approved_edited_or_rejected(self):
        items = initialize_review_items(DETECTED_TERMS, model="qwen3:8b")
        audit = []

        self.assertFalse(review_gate_status(items)["ready"])
        apply_review_action(items, audit, "GTM", "approve", timestamp="2026-06-07T12:00:00Z")
        apply_review_action(items, audit, "ARR", "edit", edited_text="Predictable yearly subscription revenue.")
        apply_review_action(items, audit, "motion", "reject")

        gate = review_gate_status(items)

        self.assertTrue(gate["ready"])
        self.assertEqual(gate["pending"], 0)
        self.assertEqual(gate["reviewed"], 3)
        self.assertEqual(gate["total"], 3)


if __name__ == "__main__":
    unittest.main()
