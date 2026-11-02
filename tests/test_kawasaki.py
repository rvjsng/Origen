import os, sys, math, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constraints.kawasaki import check_kawasaki


def deg(*v):
    return [math.radians(x) for x in v]


class TestKawasaki(unittest.TestCase):
    def test_exact_valid(self):
        self.assertTrue(check_kawasaki(deg(90, 90, 90, 90)).passed)
        # A+C = 70+110 = 180 = B+D = 95+85
        self.assertTrue(check_kawasaki(deg(70, 95, 110, 85)).passed)
        self.assertTrue(check_kawasaki(deg(30, 60, 90, 30, 60, 90)).passed)  # 6 sectors

    def test_invalid(self):
        self.assertFalse(check_kawasaki(deg(60, 120, 60, 120)).passed)
        self.assertFalse(check_kawasaki(deg(100, 100, 100, 60)).passed)

    def test_tolerance(self):
        a = deg(90, 90, 90, 90)
        a[0] += 1e-8  # within 1e-6 rad
        self.assertTrue(check_kawasaki(a, tolerance=1e-6).passed)
        b = deg(90, 90, 90, 90)
        b[0] += math.radians(0.01)  # ~1.7e-4 rad: outside
        r = check_kawasaki(b, tolerance=1e-6)
        self.assertFalse(r.passed)
        self.assertGreater(r.error, 1e-6)

    def test_float_roundoff_passes(self):
        a = [math.radians(36)] * 10
        self.assertTrue(check_kawasaki(a).passed)

    def test_odd_and_empty_not_applicable(self):
        for s in (deg(120, 120, 120), []):
            r = check_kawasaki(s)
            self.assertFalse(r.passed)
            self.assertFalse(r.applicable)

    def test_dict_keys(self):
        d = check_kawasaki(deg(90, 90, 90, 90), vertex_id=3).to_dict()
        for k in ["check", "status", "sector_angles_deg", "odd_sum_deg", "even_sum_deg", "error_deg", "explanation"]:
            self.assertIn(k, d)


if __name__ == "__main__":
    unittest.main()
