from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
import numpy as np
import astropy.units as u
from astropy.time import Time, TimeDelta
from astropy.utils import iers
from astropy.table import Table

import SKEDTools
import SKEDTools_vex
import SKED_GUITool
import SKED_GUITool_vex
from schedule_validation import validate_schedule
from xml_conversion import convert_xml
from iers_status import check_iers
from test_schedule_app import Page, create_session

FIXTURES = Path(__file__).parent / 'fixtures'


class WorkflowTests(unittest.TestCase):
    def test_failed_paste_preserves_existing_schedule(self):
        for cls, filename in [(SKEDTools.DRG, 'u23168a.DRG'), (SKEDTools_vex.VEX, 'r26109a.vex')]:
            with self.subTest(filename=filename):
                model = cls()
                text = (FIXTURES / filename).read_text()
                model.readtxt('\ufeff' + text.replace('\n', '\r\n'))
                original = model.output()
                with self.assertRaises(Exception):
                    model.readtxt('$EXPER\ninvalid')
                self.assertEqual(model.output(), original)

    def test_web_controls_and_paste(self):
        for editor, cls, filename, key in [(SKED_GUITool, SKEDTools.DRG, 'u23168a.DRG', 'drg'),
                                           (SKED_GUITool_vex, SKEDTools_vex.VEX, 'r26109a.vex', 'vex')]:
            session = create_session(editor, web=True)
            self.assertTrue(session['file_imp'].disabled)
            self.assertTrue(session['file_exp'].disabled)
            page = session['page']
            session['import_fromtxt'](None)
            dialog = page.dialog
            field = dialog.content.content.controls[0]
            field.value = (FIXTURES / filename).read_text()
            dialog.actions[0].on_click(None)
            self.assertFalse(dialog.open)
            self.assertTrue(session[key].output())
            session['copy_clip'](None)
            self.assertTrue(page.dialog.open)
            self.assertIn('$', page.dialog.content.content.controls[1].value)

    def test_vera_requires_four_stations(self):
        model = SKEDTools_vex.VEX()
        model.read(FIXTURES / 'r26109a.vex')
        validate_schedule(model, vera=True)
        model.sched.list[0].station = model.sched.list[0].station[:3]
        with self.assertRaisesRegex(ValueError, 'four stations'):
            validate_schedule(model, vera=True)

    def test_jvn_reorders_same_array_and_rejects_different_array(self):
        model = SKEDTools.DRG()
        model.read(FIXTURES / 'u23168a.DRG')
        model.sked.skeds[1].stations.reverse()
        validate_schedule(model)
        model.adjust()
        self.assertEqual([a.code for a in model.sked.skeds[0].antennas], [a.code for a in model.sked.skeds[1].antennas])
        model.sked.skeds[1].stations.pop()
        with self.assertRaisesRegex(ValueError, 'same stations'):
            validate_schedule(model)

    def test_xml_isolated_and_invalid_options_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'generator.py'
            script.write_text("from pathlib import Path\nPath('schedule.xml').write_text('<schedule/>')\n")
            args = dict(frequency='C', recorder='vsrec', scans='1', length='1', fft='1024', script=script)
            text = (FIXTURES / 'u23168a.DRG').read_text()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: convert_xml(text, **args), range(2)))
            self.assertEqual(results, [{'schedule.xml': '<schedule/>'}] * 2)
            self.assertFalse((Path(directory) / 'schedule.xml').exists())
            for field, value in [('scans', '1; touch bad'), ('fft', '3'), ('delay', 'nan')]:
                with self.assertRaises(ValueError):
                    convert_xml(text, **dict(args, **{field: value}))

    def test_iers_predictions_range_and_network_errors(self):
        scans = [SimpleNamespace(start=Time('2024-01-01'), dur=TimeDelta(60, format='sec'))]
        class FakeTable:
            meta = {'data_url': 'test-table'}
            def __getitem__(self, key):
                return np.array([59000, 62000]) * u.day
            def ut1_utc(self, times, return_status=False):
                if return_status:
                    return np.zeros(2), np.array([status, status])
                return np.zeros(2)
            def pm_xy(self, times, return_status=False):
                return np.zeros(2), np.zeros(2), np.array([status, status])
        status = iers.FROM_IERS_A_PREDICTION
        with patch('iers_status.iers.IERS_Auto.open', return_value=FakeTable()):
            self.assertIn('predicted values', check_iers(scans))
            status = iers.TIME_BEYOND_IERS_RANGE
            with self.assertRaisesRegex(ValueError, 'outside the IERS data range'):
                check_iers(scans)
        with patch('iers_status.iers.IERS_Auto.open', side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError, 'Failed to retrieve or update'):
                check_iers(scans)
