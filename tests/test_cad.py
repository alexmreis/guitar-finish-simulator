import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

class CadTests(unittest.TestCase):
    def test_imports_actual_closed_cad_outline_in_millimeters(self):
        from guitar_finish_simulator.cad import read_outline
        outline = read_outline(ROOT / 'geometry/body_outline.dxf', layer='BODY', units='mm')
        self.assertEqual(len(outline), 320)
        self.assertAlmostEqual(max(p[0] for p in outline)-min(p[0] for p in outline), 320, places=6)
        self.assertAlmostEqual(max(p[1] for p in outline)-min(p[1] for p in outline), 439.738, delta=.01)

    def test_rejects_open_and_crossing_contours_before_meshing(self):
        from guitar_finish_simulator.cad import read_outline
        from guitar_finish_simulator.project import SpecificationError
        for closed, points in [(0, [(0,0),(40,0),(40,60),(0,60)]), (1, [(0,0),(40,60),(0,60),(40,0)])]:
            with self.subTest(closed=closed), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'invalid.dxf'
                text = '0\nLWPOLYLINE\n8\nBODY\n70\n'+str(closed)+'\n'
                text += ''.join(f'10\n{x}\n20\n{y}\n' for x,y in points)
                path.write_text(text+'0\nEOF\n')
                with self.assertRaises(SpecificationError):
                    read_outline(path)

    def test_svg_polygon_uses_declared_units_and_cartesian_y(self):
        from guitar_finish_simulator.cad import read_outline
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'body.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><polygon id="BODY" points="-1,0 1,0 1,-3 -1,-3"/></svg>')
            points=read_outline(path, units='in')
            self.assertEqual(points,[(-25.4,0),(25.4,0),(25.4,76.19999999999999),(-25.4,76.19999999999999)])

    def test_named_cad_points_preserve_hardware_locations_in_mm(self):
        from guitar_finish_simulator.cad import read_anchors
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'anchors.dxf'
            path.write_text('0\nSECTION\n2\nENTITIES\n0\nPOINT\n8\nBRIDGE\n10\n0\n20\n-72\n0\nPOINT\n8\nVOLUME\n10\n70\n20\n-90\n0\nENDSEC\n0\nEOF\n')
            self.assertEqual(read_anchors(path,units='mm'),{'BRIDGE':[0,-72],'VOLUME':[70,-90]})
