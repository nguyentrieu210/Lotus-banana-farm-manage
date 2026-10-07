import unittest
from lotus_farm.promax_rules import geometry, point_in_geometry, coordinates, work_completion, vintage_choice, split_amount, weighted_packout
from lotus_farm.rules import RuleError


class ProMaxRules(unittest.TestCase):
    def test_map_hole_boundary_and_crossed_ring(self):
        g={'type':'Polygon','coordinates':[[[0,0],[4,0],[4,4],[0,4],[0,0]],[[1,1],[2,1],[2,2],[1,2],[1,1]]]}
        self.assertTrue(point_in_geometry(3,3,g));self.assertTrue(point_in_geometry(0,0,g))
        self.assertFalse(point_in_geometry(1.5,1.5,g));self.assertFalse(point_in_geometry(5,5,g))
        for ring in ([[0,0],[1,0],[0,0]],[[0,0],[2,2],[0,2],[2,0],[0,0]]):
            with self.assertRaises(RuleError):geometry({'type':'Polygon','coordinates':[ring]})
        with self.assertRaises(RuleError):coordinates('NaN',0)

    def test_completion_does_not_sum_incompatible_units(self):
        self.assertEqual(work_completion([dict(planned_qty=1000,completed_qty=500),dict(planned_qty=2,completed_qty=2)]),75)
        self.assertIsNone(work_completion([]))

    def test_snapshot_after_cutoff_is_not_used(self):
        samples=[dict(name='early',released_at='2026-08-01 10:00:00'),dict(name='late',released_at='2026-09-20 10:00:00')]
        self.assertEqual(vintage_choice(samples,'2026-10-01',8)['name'],'early')
        self.assertEqual(vintage_choice(samples,'2026-10-01',1)['name'],'late')
        self.assertIsNone(vintage_choice(samples,'2026-10-01',12))

    def test_partial_conversion_and_weighted_yield(self):
        self.assertEqual(split_amount(100,40,30),(30,70))
        with self.assertRaises(RuleError):split_amount(100,40,50)
        result=weighted_packout([dict(input_kg=100,finished_kg=50),dict(input_kg=900,finished_kg=810)],2)
        self.assertEqual(result['packout_rate_percent'],86)
        with self.assertRaises(RuleError):weighted_packout([],1)

    def test_kml_keeps_names_without_guessing_farm(self):
        from lotus_farm.promax_rules import kml_geometries
        data=b'<kml xmlns="http://www.opengis.net/kml/2.2"><Placemark><name>legacy plot</name><Polygon><outerBoundaryIs><LinearRing><coordinates>106,10,0 107,10,0 107,11,0 106,10,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></kml>'
        result=kml_geometries(data)
        self.assertEqual(result[0]['name'],'legacy plot');self.assertEqual(result[0]['geometry']['type'],'Polygon')
        self.assertNotIn('farm',result[0])
        with self.assertRaises(RuleError):kml_geometries(b'<!DOCTYPE kml><kml/>')
