import os, sys, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constraints.maekawa import check_maekawa


class TestMaekawa(unittest.TestCase):
    def test_valid(self):
        for m, v in [(3, 1), (1, 3), (4, 2), (5, 3)]:
            r = check_maekawa(m, v)
            self.assertTrue(r.passed, (m, v))
            self.assertEqual(r.status, "PASS")
            self.assertEqual(r.difference, 2)

    def test_invalid(self):
        for m, v in [(2, 2), (3, 2), (6, 3), (4, 0)]:
            r = check_maekawa(m, v)
            self.assertFalse(r.passed, (m, v))
            self.assertEqual(r.status, "FAIL")

    def test_zero_folds_fails(self):
        self.assertFalse(check_maekawa(0, 0).passed)

    def test_vertex_id_and_dict(self):
        r = check_maekawa(3, 1, vertex_id=42)
        self.assertEqual(r.vertex_id, 42)
        for k in ["check", "status", "mountain_count", "valley_count", "difference", "explanation"]:
            self.assertIn(k, r.to_dict())

    def test_explanation_does_not_overclaim(self):
        self.assertIn("necessary", check_maekawa(3, 1).explanation.lower())


if __name__ == "__main__":
    unittest.main()
