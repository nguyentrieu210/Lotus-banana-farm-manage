import unittest
from lotus_farm.promax_rules import geometry, coordinates
from lotus_farm.rules import RuleError


class ProMaxRules(unittest.TestCase):
    def test_map_polygon_with_hole_and_crossed_ring(self):
        g={'type':'Polygon','coordinates':[[[0,0],[4,0],[4,4],[0,4],[0,0]],[[1,1],[2,1],[2,2],[1,2],[1,1]]]}
        self.assertEqual(geometry(g),g)
        for ring in ([[0,0],[1,0],[0,0]],[[0,0],[2,2],[0,2],[2,0],[0,0]]):
            with self.assertRaises(RuleError):geometry({'type':'Polygon','coordinates':[ring]})
        with self.assertRaises(RuleError):coordinates('NaN',0)
