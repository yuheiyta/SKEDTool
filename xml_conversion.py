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
        raise FileNotFoundError('XML converter is not bundled. Configure an authorized mk_xml.py script.')
    text = normalize_text(text)
    if frequency not in ('C', 'X') or recorder not in ('vsrec', 'octadisk'):
        raise ValueError('Select Frequency and Recorder.')
    scans = [int(value) for value in str(scans).replace(',', ' ').split()]
    length, fft = int(length), int(fft)
    delay, rate = float(delay), float(rate)
    if not scans or min(scans) < 1 or length < 1 or fft < 2 or fft & (fft - 1):
        raise ValueError('Scan and Length must be positive integers; FFT must be a power of two, at least 2.')
    if not math.isfinite(delay) or not math.isfinite(rate):
        raise ValueError('Delay and Rate must be finite numbers.')
    scan_lines = [line for line in text.splitlines() if 'PREOB' in line and not line.startswith('*')]
    if max(scans) > len(scan_lines):
        raise ValueError('The requested scan does not exist.')
    with tempfile.TemporaryDirectory(prefix='schedule-xml-') as directory:
        working = Path(directory)
        (working / 'schedule.DRG').write_text(text, encoding='utf-8')
        args = [sys.executable, str(script), '--drg', 'schedule.DRG', '--frequency', frequency,
                '--type', '1', '--recorder', recorder, '--recstart', '0',
                '--delay', str(delay), '--rate', str(rate), '--scan', *map(str, scans),
                '--length', str(length), '--fft', str(fft), '-y']
        result = subprocess.run(args, cwd=working, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError('XML generation failed: ' + (result.stderr or result.stdout)[-2000:])
        outputs = {}
        for path in sorted(working.glob('*.xml')):
            content = path.read_text(encoding='utf-8')
            ET.fromstring(content)
            outputs[path.name] = content
        if not outputs:
            raise RuntimeError('No XML was generated: ' + result.stdout[-2000:])
        return outputs
