import io
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table
import astropy.units as u

import SKEDTools
from calibrator_catalog import search_catalog
from astronomy_helpers import simbad_coordinate


class CatalogTests(unittest.TestCase):
    def test_numeric_separation_order_and_no_shared_mutation(self):
        coordinates = SkyCoord([10, 2] * u.deg, [0, 0] * u.deg)
        rows = np.full((2, 18), '1.0', dtype='<U20')
        rows[:, 0] = ['far', 'near']
        rows[0, 8] = '--'
        rows.setflags(write=False)
        with patch('calibrator_catalog.load_catalog', return_value=(coordinates, rows)):
            _, found = search_catalog(SkyCoord(0*u.deg, 0*u.deg), 0.1, 0, 12)
            self.assertEqual(list(found[:, 0]), ['2.00', '10.00'])
            self.assertEqual(list(found[:, 1]), ['near', 'far'])
            self.assertEqual(rows[0, 8], '--')
            with self.assertRaisesRegex(ValueError, '見つかりません'):
                search_catalog(SkyCoord(90*u.deg, 0*u.deg), 0.1, 0.32, 2.2)

    def test_both_simbad_formats(self):
        old = Table({'RA': ['12 00 00'], 'DEC': ['-00 30 00']})
        new = Table({'ra': [180.0], 'dec': [-0.5]})
        self.assertLess(simbad_coordinate(old).separation(simbad_coordinate(new)).arcsec, 1e-6)

    def test_drg_write_keeps_caller_stream_open(self):
        drg = SKEDTools.DRG()
        drg.read(Path(__file__).parent / 'fixtures/u23168a.DRG')
        stream = io.StringIO()
        drg.write(stream)
        self.assertEqual(stream.getvalue(), drg.output() + '\n')
