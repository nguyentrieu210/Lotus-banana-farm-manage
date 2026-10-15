import unittest
from lotus_farm.hr_rules import (
    normalize_cccd, normalized_phone, transition_allowed,
    onboarding_gaps, WORKER_CATEGORIES, PAYMENT_BASES
)

class HRRulesTest(unittest.TestCase):
    def test_cccd(self):
        self.assertEqual(normalize_cccd(" 0123-4567 8901 "), "012345678901")
        for value in ("", "123", "1234567890123", "abcdefgh1234", "٠١٢٣٤٥٦٧٨٩٠١"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_cccd(value)

            with self.subTest(value="non-ascii digits"), self.assertRaises(ValueError):
                normalize_cccd("٠١٢٣٤٥٦٧٨٩٠١")

    def test_phone(self):
        self.assertEqual(normalized_phone("0382 397 073"), "0382397073")
        self.assertEqual(normalized_phone("+84 382 397 073"), "+84382397073")
        for value in ("", "abc", "012"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalized_phone(value)

    def test_recruitment_states(self):
        self.assertTrue(transition_allowed("New", "Screening"))
        self.assertTrue(transition_allowed("Screening", "Hold"))
        self.assertTrue(transition_allowed("Hold", "Interview"))
        self.assertTrue(transition_allowed("Offered", "Hired"))
        self.assertFalse(transition_allowed("New", "Hired"))
        self.assertFalse(transition_allowed("Hired", "New"))

    def test_onboarding_missing(self):
        self.assertIn("CCCD", onboarding_gaps({}))
        full = {k: "ok" for k in ("lotus_cccd_hash", "lotus_id_issue_on", "lotus_id_issue_at", "cell_number", "current_address", "lotus_emergency_name", "lotus_emergency_phone", "designation", "lotus_worker_category", "lotus_payment_basis")}
        self.assertEqual(onboarding_gaps(full), [])

    def test_contractors_not_labeled_employees(self):
        self.assertIn("Seasonal", WORKER_CATEGORIES)
        self.assertIn("Piecework", PAYMENT_BASES)
        self.assertNotIn("Contractor", WORKER_CATEGORIES)

if __name__ == "__main__":
    unittest.main()
