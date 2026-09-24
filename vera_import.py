"""Restrict mixed-network VEX input to the four VERA stations before parsing."""
import re
from schedule_text import normalize_text
from schedule_validation import VERA_STATIONS

SECTION = re.compile(r'(?m)^\s*\$([A-Z_]+)\s*;')
DEFINITION = re.compile(r'(?ms)^\s*def\s+([^;\s]+)\s*;.*?^\s*enddef\s*;')


def vera_only_text(text):
    text = normalize_text(text)
    matches = list(SECTION.finditer(text))
    blocks = {match[1]: text[match.end():matches[i+1].start() if i+1 < len(matches) else len(text)]
              for i, match in enumerate(matches)}
    if len(blocks) != len(matches):
        raise ValueError('Duplicate VEX sections are not supported.')
    if 'STATION' not in blocks or 'SCHED' not in blocks:
        raise ValueError('VEX must contain $STATION and $SCHED sections.')
    stations = {m[1]: m[0] for m in DEFINITION.finditer(blocks['STATION'])}
    missing = set(VERA_STATIONS) - stations.keys()
    if missing:
        raise ValueError('Missing VERA station definitions: ' + ', '.join(sorted(missing)))
    removed = set(stations) - set(VERA_STATIONS)
    refs = {'SITE': set(), 'ANTENNA': set(), 'DAS': set()}
    for code in VERA_STATIONS:
        active = re.sub(r'(?m)\*[^\n]*', '', stations[code])
        for section, name in re.findall(r'ref\s+\$(SITE|ANTENNA|DAS)\s*=\s*([^;\s]+)\s*;', active):
            refs[section].add(name)
    blocks['STATION'] = '\n' + '\n'.join(stations[code] for code in VERA_STATIONS) + '\n'
    for section, names in refs.items():
        if section not in blocks or not names:
            raise ValueError('Missing VERA ' + section + ' information.')
        blocks[section] = DEFINITION.sub(lambda m: m[0] if m[1] in names else '', blocks[section])
    def scan(match):
        content = match[0]
        present = []
        def station(line):
            code = line[1].strip()
            if code in VERA_STATIONS:
                present.append(code)
                return line[0]
            removed.add(code)
            return ''
        content = re.sub(r'(?m)^\s*station\s*=\s*([^:;]+):[^;]*;', station, content)
        if set(present) != set(VERA_STATIONS) or len(present) != 4:
            raise ValueError(f'Scan {match[1]} must contain Vm, Vr, Vo and Vs exactly once.')
        return re.sub(r'(?m)^(\s*)source\s*=', r'\1source1 =', content)
    blocks['SCHED'] = re.sub(r'(?ms)^\s*scan\s+([^;\s]+)\s*;.*?^\s*endscan\s*;', scan, blocks['SCHED'])
    # Remove non-VERA qualifiers (and references applying exclusively to other stations).
    def mode_ref(match):
        values = [item.strip() for item in match[2].split(':')]
        if len(values) == 1:
            return match[0]
        kept = [code for code in values[1:] if code in VERA_STATIONS]
        return f'{match[1]} = ' + ':'.join([values[0]] + kept) + ';' if kept else ''
    if 'MODE' in blocks:
        blocks['MODE'] = re.sub(r'(?m)^(\s*ref\s+\$\w+)\s*=\s*([^;]+);', mode_ref, blocks['MODE'])
    result = text[:matches[0].start()] + ''.join('$' + match[1] + ';\n' + blocks[match[1]] for match in matches)
    return result, sorted(removed)
