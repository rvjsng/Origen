import os, sys, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.crease_pattern import CreasePattern, MOUNTAIN, VALLEY
from constraints.topology import check_topology


def star():
    cp = CreasePattern(100.0)
    c = cp.add_vertex((50, 50))
    for pt, a in [((50, 0), MOUNTAIN), ((100, 50), VALLEY), ((50, 100), MOUNTAIN), ((0, 50), MOUNTAIN)]:
        cp.add_crease(c, cp.add_vertex(pt), a)
    return cp, c


class TestTopology(unittest.TestCase):
    def test_connected_passes(self):
        cp, _ = star()
        r = check_topology(cp)
        self.assertTrue(r.passed)
        self.assertTrue(r.checks["connected"])

    def test_disconnected_fails(self):
        cp, _ = star()
        a, b = cp.add_vertex((10, 10)), cp.add_vertex((20, 20))
        cp.add_crease(a, b, MOUNTAIN)
        r = check_topology(cp)
        self.assertFalse(r.passed)
        self.assertFalse(r.checks["connected"])

    def test_isolated_vertex_fails(self):
        cp, _ = star()
        cp.add_vertex((99, 1))
        r = check_topology(cp)
        self.assertFalse(r.passed)
        self.assertTrue(r.checks["isolated_vertices"])

    def test_low_degree_interior_fails(self):
        cp = CreasePattern(100.0)
        c = cp.add_vertex((50, 50))
        cp.add_crease(c, cp.add_vertex((50, 0)), MOUNTAIN)
        cp.add_crease(c, cp.add_vertex((100, 50)), VALLEY)
        r = check_topology(cp)
        self.assertFalse(r.passed)
        self.assertIn(c, r.checks["low_degree_interior_vertices"])

    def test_empty_graph_fails(self):
        self.assertFalse(check_topology(CreasePattern(100.0)).passed)


if __name__ == "__main__":
    unittest.main()
