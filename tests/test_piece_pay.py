"""Pure unit checks: piece payment is never based on headcount or workdays."""
import unittest
from lotus_farm.piece_pay import accepted_output, piece_amount
from lotus_farm.rules import RuleError


class PiecePayTests(unittest.TestCase):
    def test_eight_hundred_bunches_at_four_thousand_vnd(self):
        self.assertEqual(piece_amount(800, 4000), 3_200_000)
        self.assertEqual(accepted_output(800, 800), 800)

    def test_partial_acceptance_requires_explanation(self):
        self.assertEqual(accepted_output(850, 800, "50 damaged bags"), 800)
        with self.assertRaises(RuleError):
            accepted_output(850, 800)
        with self.assertRaises(RuleError):
            accepted_output(850, 900, "invalid")
        with self.assertRaises(RuleError):
            accepted_output(-1, 0)
        with self.assertRaises(RuleError):
            accepted_output(100, -1)

    def test_only_final_vnd_amount_rounded(self):
        self.assertEqual(piece_amount("2.5", "100.2"), 251)
        self.assertEqual(piece_amount(3, "0.5"), 2)
        with self.assertRaises(RuleError):
            piece_amount(10, 0)
        with self.assertRaises(RuleError):
            piece_amount("nan", 4000)
        with self.assertRaises(RuleError):
            piece_amount(5, -200)

    def test_same_output_is_paid_the_same_regardless_of_workers(self):
        for worker_count in (1, 10, 50):
            self.assertEqual(piece_amount(800, 4000), 3_200_000, worker_count)


if __name__ == "__main__":
    unittest.main()

