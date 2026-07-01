import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mentor_that_knows.dsl import Particle, Step, braid, collide, evaluate_chain, glyph, mirror


class DslTests(unittest.TestCase):
    def test_glyph_wraps(self):
        self.assertEqual(glyph(9), "nul")
        self.assertEqual(glyph(-1), "hex")

    def test_mirror(self):
        self.assertEqual(glyph(mirror(0)), "hex")
        self.assertEqual(glyph(mirror(8)), "nul")

    def test_braid(self):
        self.assertEqual(glyph(braid(3, 6)), "fen")

    def test_chain_with_heat_slip(self):
        trace = evaluate_chain(0, [Step("tilt", amount=2)], heat_slip=True)
        self.assertEqual(trace.compact(), "nul -> avo")
        self.assertIn("heat slip", trace.detailed())

    def test_collision(self):
        trace = collide(Particle(2, 1), Particle(7, 0))
        self.assertEqual(trace.final.render(), "emi:calm")


if __name__ == "__main__":
    unittest.main()
