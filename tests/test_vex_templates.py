import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from SKEDTools_vex import VEX
from vex_templates import build_template, load_template, apply_template, parse_template
from test_schedule_app import create_session
import SKED_GUITool_vex

FIXTURE = Path(__file__).parent / 'fixtures' / 'r26109a.vex'


class TemplateTests(TestCase):
    def test_all_bundled_templates_select_without_legacy_files(self):
        session = create_session(SKED_GUITool_vex)
        options = session['modeselect'].options
        names = [option.text for option in options]
        self.assertEqual(len(names), 19)
        self.assertEqual(len(set(names)), 19)
        self.assertTrue(names[-1].startswith('KQ_'))
        for option in options:
            with self.subTest(name=option.text):
                session['modeselect'].value = option.key
                session['mode_changed'](None)
                expected, _ = parse_template(
                    session['observing_templates'][option.key]['vex'])
                for attr in ('header', 'mode', 'freq', 'procedures', 'if_', 'bbc', 'das'):
                    self.assertEqual(getattr(session['vex'], attr).output(),
                                     getattr(expected, attr).output())
                self.assertEqual({s.defname for s in session['vex'].station.list},
                                 {'Vm', 'Vr', 'Vo', 'Vs'})

    def test_settings_preserved_and_sample_observation_removed(self):
        data = build_template(FIXTURE.read_text(), 'My mode')
        template = VEX()
        template.readtxt(data['vex'])
        self.assertFalse(template.sched.list)
        self.assertFalse(template.source.list)
        self.assertEqual(template.exper.list[0].defname, 'template')
        loaded = load_template(json.dumps(data))
        self.assertEqual(loaded['name'], 'My mode')
        self.assertEqual(loaded['source_sha256'], data['source_sha256'])
        original = VEX()
        original.read(FIXTURE)
        self.assertEqual(template.freq.output(), original.freq.output())
        self.assertEqual(template.procedures.output(), original.procedures.output())

    def test_application_preserves_experiment_and_rejects_existing_scans(self):
        data = build_template(FIXTURE.read_text(), 'Display only')
        original = VEX()
        original.read(FIXTURE)
        before = original.output()
        with self.assertRaisesRegex(ValueError, 'before adding scans'):
            apply_template(original, data)
        self.assertEqual(original.output(), before)
        original.sched.list = []
        exper, source = original.exper, original.source
        apply_template(original, data)
        self.assertIs(original.exper, exper)
        self.assertIs(original.source, source)
        self.assertEqual([m.defname for m in original.mode.list], data['modes'])

    def test_missing_sections_and_references_rejected(self):
        text = FIXTURE.read_text()
        with self.assertRaisesRegex(ValueError, 'Missing sections'):
            build_template('$FREQ;\n', 'Incomplete')
        with self.assertRaises(ValueError):
            build_template(text.replace('ref $FREQ =', 'ref $FREQ = MISSING'), 'Broken')

    def test_session_selects_prebuilt_template(self):
        session = create_session(SKED_GUITool_vex)
        data = build_template(FIXTURE.read_text(), 'My mode')
        session['observing_templates']['My mode'] = data
        session['modeselect'].value = 'My mode'
        session['mode_changed'](None)
        self.assertEqual([m.defname for m in session['vex'].mode.list], data['modes'])
        self.assertNotIn('import_observing_template', session)
        self.assertNotIn('custom_select', session)
