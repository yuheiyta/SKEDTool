"""Exercise the direction actually used by VEX.check without IERS downloads."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time, TimeDelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from SKEDTools_vex import VEX


class BeamMidpointTests(unittest.TestCase):
    def test_check_uses_spherical_midpoint(self):
        cases = [
            (359, 0, 1, 0),       # RA wraps at midnight.
            (10, 89, 90, 89),     # Near the celestial pole.
            (120, -30, 121, -29), # Ordinary field.
            (120, -30, 120, -30), # Coincident directions remain finite.
        ]
        for ra1, dec1, ra2, dec2 in cases:
            with self.subTest(coords=(ra1, dec1, ra2, dec2)):
                first = SkyCoord(ra1 * u.deg, dec1 * u.deg)
                second = SkyCoord(ra2 * u.deg, dec2 * u.deg)
                antenna = SimpleNamespace(
                    beam_lim=[0 * u.deg, 180 * u.deg],
                    lim=[[-360, 360], [-90, 90]], coord=None,
                )
                scan = SimpleNamespace(
                    src=[SimpleNamespace(coord=first), SimpleNamespace(coord=second)],
                    antennas=[antenna], start=Time('2026-01-01T12:00:00'),
                    dur=TimeDelta(60 * u.s),
                )
                vex = VEX(sched=SimpleNamespace(list=[scan]))
                directions = []

                def capture_direction(coordinate, frame):
                    directions.append(coordinate)
                    return SimpleNamespace(
                        alt=SimpleNamespace(deg=45), az=SimpleNamespace(deg=180)
                    )

                with patch.object(SkyCoord, 'transform_to', autospec=True,
                                  side_effect=capture_direction):
                    self.assertEqual(vex.check(), ['check: OK'])
                self.assertEqual(len(directions), 2)
                half_sep = first.separation(second).deg / 2
                for midpoint in directions:
                    self.assertAlmostEqual(midpoint.separation(first).deg, half_sep, places=9)
                    self.assertAlmostEqual(midpoint.separation(second).deg, half_sep, places=9)


if __name__ == '__main__':
    unittest.main()
