"""Validate the supported fixed-array scheduling model before calculation/export."""
import math

VERA_STATIONS = ('Vm', 'Vr', 'Vo', 'Vs')


def validate_schedule(schedule, vera=False):
    schedule.adjust()
    scans = schedule.sched.list if vera else schedule.sked.skeds
    if not scans:
        raise ValueError('No scans are defined.')
    common = None
    for index, scan in enumerate(scans, 1):
        codes = scan.antcodes if vera else scan.stations
        if not codes or len(codes) != len(set(codes)):
            raise ValueError(f'Scan {index}: Stations are missing or duplicated.')
        if vera and set(codes) != set(VERA_STATIONS):
            raise ValueError(f'Scan {index}: VERA requires all four stations: Vm, Vr, Vo, Vs.')
        if common is None:
            common = set(codes)
        elif set(codes) != common:
            raise ValueError('Use the same stations for every scan.')
        # The legacy slew calculation indexes antennas by position.
        order = {code: i for i, code in enumerate(VERA_STATIONS if vera else sorted(common))}
        if len(scan.antennas) != len(codes):
            raise ValueError(f'Scan {index}: Station information could not be resolved.')
        scan.antennas = [ant for _, ant in sorted(zip(codes, scan.antennas), key=lambda item: order[item[0]])]
        if vera:
            scan.station = sorted(scan.station, key=lambda line: order[line.split(':')[0].strip()])
        else:
            scan.stations = sorted(codes)
        if not math.isfinite(float(scan.dur.sec)) or scan.dur.sec <= 0:
            raise ValueError(f'Scan {index}: Duration must be positive.')
        if vera:
            if any(abs(float(duration.sec) - float(scan.dur.sec)) > 1e-6 for duration in scan.durlist):
                raise ValueError(f'Scan {index}: All stations must have the same duration.')
            if any(float(station.split(':')[1].replace('sec', '').strip()) != 0 for station in scan.station):
                raise ValueError(f'Scan {index}: Station-specific start offsets are not supported.')
    return scans
