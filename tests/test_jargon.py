import unittest

from src.jargon import detect_terms, merge_terms


DEMO_TRANSCRIPT = (
    "Let's revisit our GTM motion before Q3 and improve ARR through our PLG "
    "initiative while reducing churn across enterprise accounts."
)


class JargonDetectionTests(unittest.TestCase):
    def test_demo_transcript_detects_required_terms(self):
        terms = detect_terms(DEMO_TRANSCRIPT)

        by_term = {term["term"].lower(): term for term in terms}

        self.assertEqual(by_term["gtm"]["canonical"], "Go-to-Market")
        self.assertEqual(by_term["q3"]["canonical"], "Third quarter")
        self.assertEqual(by_term["arr"]["canonical"], "Annual Recurring Revenue")
        self.assertEqual(by_term["plg"]["canonical"], "Product-Led Growth")
        self.assertEqual(by_term["churn"]["canonical"], "Customer Churn")
        self.assertEqual(by_term["enterprise accounts"]["canonical"], "Large business customers")

    def test_unknown_acronym_is_review_required(self):
        terms = detect_terms("We need SOC2 before Q4.")
        by_term = {term["term"].lower(): term for term in terms}

        self.assertEqual(by_term["soc2"]["canonical"], "Unknown acronym")
        self.assertEqual(by_term["soc2"]["source"], "regex")
        self.assertTrue(by_term["soc2"]["needs_review"])

    def test_heuristics_find_corporate_candidates(self):
        terms = detect_terms("We should operationalize the new growth motion.")
        by_term = {term["term"].lower(): term for term in terms}

        self.assertEqual(by_term["operationalize"]["source"], "heuristic")
        self.assertTrue(by_term["operationalize"]["needs_review"])
        self.assertEqual(by_term["growth motion"]["source"], "heuristic")

    def test_merge_keeps_dictionary_canonical_and_accepts_confident_llm_explanation(self):
        baseline = detect_terms("We should improve ARR.")
        merged = merge_terms(
            baseline,
            [
                {
                    "term": "ARR",
                    "canonical": "Different Canonical",
                    "explanation": "Subscription revenue the business expects to receive over a year.",
                    "category": "metric",
                    "confidence": 0.88,
                    "needs_review": False,
                    "source": "llm",
                }
            ],
        )

        arr = {term["term"].lower(): term for term in merged}["arr"]

        self.assertEqual(arr["canonical"], "Annual Recurring Revenue")
        self.assertEqual(
            arr["explanation"],
            "Subscription revenue the business expects to receive over a year.",
        )
        self.assertEqual(arr["source"], "dictionary,llm")
        self.assertFalse(arr["needs_review"])


if __name__ == "__main__":
    unittest.main()
