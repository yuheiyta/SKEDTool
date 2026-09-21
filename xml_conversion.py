"""Optional adapter; the third-party XML generator is never bundled."""
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from schedule_io import normalize_text


def xml_script():
    configured = os.environ.get('SKED_XML_SCRIPT')
    return Path(configured).expanduser().resolve() if configured else Path(__file__).parent / 'mk_xml.py'


def convert_xml(text, *, frequency, recorder, scans, length, fft, delay=0, rate=0, script=None):
    script = Path(script or xml_script()).resolve()
    if not script.is_file():
        raise FileNotFoundError('XML生成ツールは同梱していません。利用許可のあるmk_xml.pyを設定してください。')
    text = normalize_text(text)
    if frequency not in ('C', 'X') or recorder not in ('vsrec', 'octadisk'):
        raise ValueError('FrequencyとRecorderを選択してください。')
    scans = [int(value) for value in str(scans).replace(',', ' ').split()]
    length, fft = int(length), int(fft)
    delay, rate = float(delay), float(rate)
    if not scans or min(scans) < 1 or length < 1 or fft < 2 or fft & (fft - 1):
        raise ValueError('Scanは1以上、Lengthは正の整数、FFTは2以上の2の累乗を指定してください。')
    if not math.isfinite(delay) or not math.isfinite(rate):
        raise ValueError('DelayとRateには有限の数値を指定してください。')
    scan_lines = [line for line in text.splitlines() if 'PREOB' in line and not line.startswith('*')]
    if max(scans) > len(scan_lines):
        raise ValueError('指定したScanが存在しません。')
    with tempfile.TemporaryDirectory(prefix='schedule-xml-') as directory:
        working = Path(directory)
        (working / 'schedule.DRG').write_text(text, encoding='utf-8')
        args = [sys.executable, str(script), '--drg', 'schedule.DRG', '--frequency', frequency,
                '--type', '1', '--recorder', recorder, '--recstart', '0',
                '--delay', str(delay), '--rate', str(rate), '--scan', *map(str, scans),
                '--length', str(length), '--fft', str(fft), '-y']
        result = subprocess.run(args, cwd=working, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError('XML生成に失敗しました: ' + (result.stderr or result.stdout)[-2000:])
        outputs = {}
        for path in sorted(working.glob('*.xml')):
            content = path.read_text(encoding='utf-8')
            ET.fromstring(content)
            outputs[path.name] = content
        if not outputs:
            raise RuntimeError('XMLが生成されませんでした: ' + result.stdout[-2000:])
        return outputs
