from pathlib import Path
import re
from threading import Event, Thread
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import SKEDTools_vex
import SKED_GUITool_vex
from test_schedule_app import create_session
from vera_import import vera_only_text

FIXTURE = Path(__file__).parent / 'fixtures' / 'r26109a.vex'


class RenderFixTests(unittest.TestCase):
    def test_mixed_network_filters_other_station_before_parsing(self):
        text = FIXTURE.read_text()
        text = text.replace('$STATION;', '$STATION;\ndef Xx;\n ref $SITE = OTHER;\n ref $ANTENNA = OTHER;\n ref $DAS = OTHER;\nenddef;')
        text = text.replace('$ANTENNA;', '$ANTENNA;\ndef OTHER;\n unsupported = anything;\nenddef;')
        text = text.replace('$SITE;', '$SITE;\ndef OTHER;\n unsupported = anything;\nenddef;')
        text = text.replace('$DAS;', '$DAS;\ndef OTHER;\n unsupported = anything;\nenddef;')
        text = re.sub(r'(?m)^(\s*station\s*=\s*)Vm(:[^\n]+)',r'\1Xx\2\n\1Vm\2',text)
        filtered, removed = vera_only_text(text)
        self.assertEqual(removed, ['Xx'])
        model = SKEDTools_vex.VEX()
        model.readtxt(filtered)
        for scan in model.sched.list:
            self.assertEqual(set(scan.antcodes), {'Vm', 'Vr', 'Vo', 'Vs'})
        self.assertNotIn('unsupported', model.output())

    def test_bad_paste_displays_error_and_keeps_dialog_open(self):
        s = create_session(SKED_GUITool_vex, web=True)
        s['import_fromtxt'](None)
        dialog = s['page'].dialog
        controls = dialog.content.content.controls
        controls[0].value = '$STATION;\n$SCHED;'
        dialog.actions[0].on_click(None)
        self.assertTrue(dialog.open)
        self.assertIn('Missing VERA', controls[1].value)

    def test_repeated_plot_does_not_duplicate_page_or_chart(self):
        s = create_session(SKED_GUITool_vex, web=True)
        page = s['page']
        chart = s['mpl']
        for _ in range(3):
            s['sourceplot'](None)
            self.assertEqual(len(page.controls), 1)
            self.assertIs(s['plt_tab'].content.content, chart)
        self.assertFalse(getattr(page, '_schedule_progress', None))

    def test_concurrent_plot_click_is_ignored_and_progress_visible(self):
        s = create_session(SKED_GUITool_vex, web=True)
        entered, release = Event(), Event()
        calls = []
        def plot():
            calls.append(1)
            self.assertTrue(s['page'].dialog.open)
            entered.set()
            self.assertTrue(release.wait(5))
            return plt.figure()
        with patch.object(s['vex'], 'sourceplot', side_effect=plot):
            thread = Thread(target=s['sourceplot'], args=(None,))
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                s['sourceplot'](None)
            finally:
                release.set()
                thread.join(5)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(s['page'].controls), 1)

    def test_failed_plot_can_be_retried(self):
        s = create_session(SKED_GUITool_vex, web=True)
        with patch.object(s['vex'], 'sourceplot', side_effect=ValueError('Test plot failure')):
            s['sourceplot'](None)
        self.assertIn('Test plot failure', s['bannertext'].value)
        self.assertIsNone(s['page']._schedule_progress)
        with patch.object(s['vex'], 'sourceplot', return_value=plt.figure()) as plot:
            s['sourceplot'](None)
        plot.assert_called_once()
        self.assertEqual(len(s['page'].controls), 1)

    def tearDown(self):
        plt.close('all')
