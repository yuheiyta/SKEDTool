import inspect
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import schedule_app
import SKEDTools
import SKEDTools_vex
from astropy.coordinates import SkyCoord


class Page:
    def __init__(self):
        self.controls = []
        self.overlay = []
        self.web = False
    def add(self, *controls):
        self.controls.extend(controls)
    def update(self):
        pass


def create_session(editor, web=False):
    captured = {}
    def capture(frame, event, arg):
        if event == 'return' and frame.f_code is editor.main.__code__:
            captured.update(frame.f_locals)
    previous = sys.getprofile()
    sys.setprofile(capture)
    try:
        page = Page()
        page.web = web
        editor.main(page)
    finally:
        sys.setprofile(previous)
    return captured


class ScheduleTests(unittest.TestCase):
    def test_sessions_do_not_share_selection(self):
        for editor in [schedule_app.SKED_GUITool, schedule_app.SKED_GUITool_vex]:
            with self.subTest(editor=editor.__name__):
                first, second = create_session(editor), create_session(editor)
                event = SimpleNamespace(control=SimpleNamespace(
                    selected=False, cells=[SimpleNamespace(content=SimpleNamespace(value=1))]
                ))
                first['skd_select'](event)
                self.assertEqual(first['selected_skd'], [1])
                self.assertEqual(second['selected_skd'], [])
                self.assertIsNot(first['src_tab'], second['src_tab'])
                self.assertIsNot(first['skd_tab'], second['skd_tab'])

    def test_drg_blank_lines_and_negative_zero(self):
        self.assertEqual(SKEDTools.Read_drg(['\n', '$SKED\n', '\n', '*\n'], 'SKED'), [])
        source = SKEDTools.Source('test', SkyCoord('12h', '-00d30m'))
        self.assertIn('-00 30', str(source))

    def test_vera_station_whitespace(self):
        vex = SKEDTools_vex.VEX()
        vex.read(str(schedule_app.ROOT / 'tests' / 'fixtures' / 'r26109a.vex'))
        for scan in vex.sched.list:
            self.assertEqual(set(scan.antcodes), {'Vm', 'Vr', 'Vo', 'Vs'})
            self.assertEqual(len(scan.antennas), 4)
        self.assertEqual(vex.output().count('station ='), len(vex.sched.list) * 4)

    def test_empty_vera_is_not_ok(self):
        vex = SKEDTools_vex.VEX(sched=SimpleNamespace(list=[]))
        self.assertEqual(vex.check(), ['No scans to check'])

    def test_launcher(self):
        page = Page()
        schedule_app.main(page)
        self.assertEqual(len(page.controls), 1)


if __name__ == '__main__':
    unittest.main()
