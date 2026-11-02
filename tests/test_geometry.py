import os, sys, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.crease_pattern import CreasePattern, MOUNTAIN, VALLEY
from constraints.geometry import check_geometry
from constraints.engine import ConstraintEngine


def good_star():
    cp = CreasePattern(100.0)
    c = cp.add_vertex((50, 50))
    for pt, a in [((50, 0), MOUNTAIN), ((100, 50), VALLEY), ((50, 100), MOUNTAIN), ((0, 50), MOUNTAIN)]:
        cp.add_crease(c, cp.add_vertex(pt), a)
    return cp


class TestGeometry(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(check_geometry(good_star()).passed)

    def test_out_of_bounds(self):
        cp = CreasePattern(100.0)
        a, b = cp.add_vertex((50, 50)), cp.add_vertex((150, 50))
        cp.add_crease(a, b, MOUNTAIN)
        r = check_geometry(cp)
        self.assertFalse(r.passed)
        self.assertIn(b, r.out_of_bounds_vertices)

    def test_zero_length(self):
        cp = CreasePattern(100.0)
        a, b = cp.add_vertex((50, 50)), cp.add_vertex((50, 50))
        cp.add_crease(a, b, MOUNTAIN)
        self.assertTrue(check_geometry(cp).zero_length_creases)

    def test_crossing_detected(self):
        cp = CreasePattern(100.0)
        a, b, c, d = (cp.add_vertex(p) for p in [(0, 0), (100, 100), (0, 100), (100, 0)])
        cp.add_crease(a, b, MOUNTAIN)
        cp.add_crease(c, d, VALLEY)
        self.assertTrue(check_geometry(cp).crossing_creases)

    def test_shared_vertex_not_a_crossing(self):
        cp = CreasePattern(100.0)
        c = cp.add_vertex((50, 50))
        cp.add_crease(c, cp.add_vertex((50, 0)), MOUNTAIN)
        cp.add_crease(c, cp.add_vertex((100, 50)), VALLEY)
        self.assertTrue(check_geometry(cp).passed)


class TestEngine(unittest.TestCase):
    def test_good_star_passes_all_stages(self):
        r = ConstraintEngine().evaluate(good_star())
        self.assertTrue(r.passed)
        self.assertIsNone(r.rejected_at_stage)

    def test_bad_maekawa_rejected_at_maekawa(self):
        cp = good_star()
        cp.graph[0][1]["assignment"] = VALLEY  # M,V,M,M -> now V,V,M,M => 2/2
        r = ConstraintEngine().evaluate(cp)
        self.assertFalse(r.passed)
        self.assertEqual(r.rejected_at_stage, "maekawa")

    def test_bad_kawasaki_rejected_at_kawasaki(self):
        cp = good_star()
        cp.set_position(1, (30, 0))  # skew one ray; M/V counts stay valid
        r = ConstraintEngine().evaluate(cp)
        self.assertEqual(r.rejected_at_stage, "kawasaki")

    def test_early_stop_skips_later_stages(self):
        cp = good_star()
        cp.add_vertex((1, 1))  # isolated vertex -> topology fails
        r = ConstraintEngine().evaluate(cp, stop_early=True)
        self.assertEqual(r.rejected_at_stage, "topology")
        self.assertIsNone(r.geometry)
        full = ConstraintEngine().evaluate(cp, stop_early=False)
        self.assertIsNotNone(full.geometry)


if __name__ == "__main__":
    unittest.main()
