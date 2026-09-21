"""Run the native DRG converter without shared input/output files."""
from pathlib import Path
import re
import os
import subprocess
import tempfile


def converter_path():
    configured = os.environ.get('SKED_DRGCONV')
    return Path(configured).expanduser().resolve() if configured else Path(__file__).parent / 'drgconv' / 'drgconv2020'


def convert_drg(text, experiment="schedule", executable=None):
    """Return {filename: SKD text}; never publish server filesystem paths."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,14}", experiment):
        raise ValueError("Experiment name must contain 1-14 letters, digits, _ or -")
    if len(text.encode("utf-8")) > 5_000_000:
        raise ValueError("DRG text is too large")
    if "\x00" in text or any(len(line.encode("utf-8")) > 510 for line in text.splitlines()):
        raise ValueError("DRG contains a NUL or a line longer than 510 bytes")
    if not all(section in text for section in ("$EXPER", "$SOURCES", "$SKED")):
        raise ValueError("DRG requires EXPER, SOURCES and SKED sections")
    executable = Path(executable or converter_path()).resolve()
    if not executable.is_file():
        raise FileNotFoundError("SKD変換器は同梱していません。利用許可のある実行ファイルをSKED_DRGCONVに設定してください。")
    with tempfile.TemporaryDirectory(prefix="schedule-drg-") as directory:
        working = Path(directory)
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        (working / (experiment + ".DRG")).write_text(normalized, encoding="utf-8")
        result = subprocess.run(
            [str(executable), experiment], cwd=working, capture_output=True,
            text=True, timeout=30, check=False,
        )
        if result.returncode:
            raise RuntimeError("DRG conversion failed: " + result.stderr[-2000:])
        outputs = {}
        for suffix in ("a.skd", "o.skd"):
            name = experiment + suffix
            path = working / name
            if not path.is_file() or not path.stat().st_size:
                raise RuntimeError("DRG converter did not produce " + name)
            outputs[name] = path.read_text(encoding="utf-8")
        return outputs
