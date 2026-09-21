from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from schedule_io import prepare_iers


class IersUiTests(TestCase):
    def test_visible_during_acquisition_and_closed_after_success_or_failure(self):
        for fails in (False, True):
            with self.subTest(fails=fails):
                frames = []
                previous = SimpleNamespace(open=False)
                page = SimpleNamespace(dialog=previous)
                page.update = lambda: frames.append(page.dialog.open)
                status = SimpleNamespace(value='')
                def acquire(scans):
                    self.assertTrue(page.dialog.open)
                    self.assertEqual(frames, [True])
                    self.assertIn('downloading if needed', status.value)
                    if fails:
                        raise ValueError('Download unavailable')
                    return 'IERS: using observed values'
                with patch('schedule_io.check_iers', side_effect=acquire):
                    if fails:
                        with self.assertRaises(ValueError):
                            prepare_iers(page, status, [object()])
                        self.assertEqual(status.value, 'Download unavailable')
                    else:
                        self.assertEqual(prepare_iers(page, status, [object()]),
                                         'IERS: using observed values')
                self.assertEqual(frames, [True, False])
                self.assertIs(page.dialog, previous)
