"""Build portable, non-pickle observing templates from complete VERA VEX files."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from schedule_text import normalize_text
from SKEDTools_vex import VEX

CUSTOM_DIR = Path(__file__).resolve().parent / 'template' / 'observing'
PARTS = {'MODE': 'mode', 'PROCEDURES': 'procedures', 'FREQ': 'freq',
         'IF': 'if_', 'BBC': 'bbc', 'STATION': 'station', 'DAS': 'das',
         'SITE': 'site', 'ANTENNA': 'antenna'}


def _sections(text):
    matches = list(re.finditer(r'(?m)^\s*\$([A-Z_]+);', text))
    sections = {}
    for i, match in enumerate(matches):
        name = match[1]
        if name in sections:
            raise ValueError(f'Duplicate section: ${name}')
        sections[name] = text[match.start():matches[i+1].start() if i+1 < len(matches) else len(text)]
    return text[:matches[0].start()] if matches else '', sections


def _statements(text):
    text = re.sub(r'(?m)\*[^\n]*', '', text)
    return Counter(re.sub(r'\s+', '', item) for item in text.split(';') if item.strip())


def parse_template(text):
    text = normalize_text(text)
    header, sections = _sections(text)
    required = set(PARTS) | {'GLOBAL', 'EXPER'}
    if required - sections.keys():
        raise ValueError('Missing sections: ' + ', '.join(sorted(required - sections.keys())))
    unknown = sections.keys() - required - {'EXPER', 'SOURCE', 'SCHED'}
    if unknown:
        raise ValueError('Unsupported sections: ' + ', '.join(sorted(unknown)))
    # The distributed examples can contain unresolved sample sources. They are not settings.
    global_text = re.sub(r'(ref\s+\$EXPER\s*=)[^;]*;', r'\1 template;', sections['GLOBAL'])
    clean = header + global_text + '\n$EXPER;\ndef template;\nenddef;\n'
    clean += ''.join(sections[key] for key in PARTS)
    clean += '\n$SOURCE;\n$SCHED;\n'
    model = VEX()
    model.readtxt(clean)
    for section, attr in PARTS.items():
        definitions = getattr(model, attr).list
        names = [item.defname for item in definitions]
        if not names or len(names) != len(set(names)):
            raise ValueError(f'Empty or duplicate definitions in ${section}')
    station_names = {item.defname for item in model.station.list}
    if station_names != {'Vm', 'Vr', 'Vo', 'Vs'}:
        raise ValueError('A VERA template must define Vm, Vr, Vo and Vs.')
    # Do not silently discard unfamiliar backend settings in the existing VEX parser.
    for section in ('MODE', 'PROCEDURES', 'FREQ', 'IF', 'BBC', 'DAS'):
        if _statements(sections[section]) != _statements(getattr(model, PARTS[section]).output()):
            raise ValueError(f'Unsupported or altered settings in ${section}')
    for section in required:
        active = re.sub(r'(?m)\*[^\n]*', '', sections[section])
        for target, value in re.findall(r'ref\s+\$([A-Z_]+)\s*=\s*([^;]+);', active):
            if target == 'EXPER':
                continue
            if target not in PARTS:
                raise ValueError(f'Unsupported reference: ${target}')
            tokens = [part.strip() for part in value.split(':')]
            names = {item.defname for item in getattr(model, PARTS[target]).list}
            if tokens[0] not in names:
                raise ValueError(f'Unresolved ${target} reference: {tokens[0]}')
            if any(station not in station_names for station in tokens[1:]):
                raise ValueError(f'Unknown station in ${target} reference')
    return model, clean


def build_template(text, name, source=''):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('A template name is required.')
    model, clean = parse_template(text)
    return {'format': 'skedtool-vera-template', 'version': 1, 'name': name.strip(),
            'source': Path(source).name, 'source_sha256': hashlib.sha256(normalize_text(text).encode()).hexdigest(),
            'modes': [item.defname for item in model.mode.list], 'vex': clean}


def load_template(text):
    data = json.loads(normalize_text(text))
    if not isinstance(data, dict) or data.get('format') != 'skedtool-vera-template' or data.get('version') != 1:
        raise ValueError('Unsupported template format.')
    validated = build_template(data['vex'], data['name'], data.get('source', ''))
    validated['source_sha256'] = data.get('source_sha256', '')
    return validated


def apply_template(schedule, data):
    if schedule.sched.list:
        raise ValueError('Apply an observing template before adding scans. Existing scans have not been changed.')
    model, _ = parse_template(data['vex'])
    settings = {attr: deepcopy(getattr(model, attr)) for attr in PARTS.values()}
    settings['header'] = deepcopy(model.header)
    schedule.__dict__.update(settings)
    schedule.glob.procedures = model.glob.procedures
    # Preserve the user's experiment and source catalogue.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='A VEX file or directory of VEX files')
    parser.add_argument('--output', type=Path, default=CUSTOM_DIR, help='Output directory (existing files are never overwritten)')
    parser.add_argument('--name', help='Display name for a single file')
    args = parser.parse_args()
    paths = (sorted(path for path in args.input.glob('*.vex')
                    if path.name.casefold() != 'verasample.vex')
             if args.input.is_dir() else [args.input])
    if not paths:
        parser.error('No .vex files found')
    if args.name and len(paths) != 1:
        parser.error('--name requires a single input file')
    args.output.mkdir(parents=True, exist_ok=True)
    failures = []
    names = json.loads((Path(__file__).resolve().parent / 'template' / 'display_names.json').read_text())
    for path in paths:
        try:
            name = args.name or names.get(path.stem.removeprefix('VERAexample_'))
            if not name:
                raise ValueError('Display name is not defined. Specify --name or add it to template/display_names.json.')
            data = build_template(path.read_text(encoding='utf-8-sig'), name, path.name)
            destination = args.output / (path.stem + '.json')
            with destination.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            print(f'Created {destination.name}: {len(data["modes"])} modes')
        except Exception as error:
            failures.append({'file': path.name, 'error': str(error)})
            print(f'Skipped {path.name}: {error}')
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
