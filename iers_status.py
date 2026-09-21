"""Preflight Earth orientation data before reporting schedule validation success."""
from threading import RLock
import numpy as np
from astropy.time import Time
from astropy.utils import iers

_LOCK = RLock()
# Keep automatic updates enabled; do not suppress stale prediction errors.
iers.conf.auto_download = True
iers.conf.remote_timeout = 10
iers.conf.auto_max_age = 30
iers.conf.iers_degraded_accuracy = "error"


def check_iers(scans):
    if not scans:
        raise ValueError('At least one scan is required to check IERS data.')
    times = Time([value.utc.mjd for scan in scans for value in (scan.start, scan.start + scan.dur)], format='mjd', scale='utc')
    with _LOCK:
        try:
            table = iers.IERS_Auto.open()
            # Without return_status, Astropy checks stale predictions and refreshes.
            table.ut1_utc(times)
            _, ut_status = table.ut1_utc(times, return_status=True)
            _, _, pm_status = table.pm_xy(times, return_status=True)
        except Exception as error:
            raise ValueError('Failed to retrieve or update IERS data. Check the connection and data availability.\n' + str(error)) from error
        if np.any(np.asarray(ut_status) < 0) or np.any(np.asarray(pm_status) < 0):
            raise ValueError('Observation times are outside the IERS data range. Cannot validate this schedule.')
        first = float(table['MJD'][0].value)
        last = float(table['MJD'][-1].value)
        predictive = np.any(np.asarray(ut_status) == iers.FROM_IERS_A_PREDICTION) or np.any(np.asarray(pm_status) == iers.FROM_IERS_A_PREDICTION)
        source = table.meta.get('data_url', 'bundled astropy-iers-data')
        return ('IERS: ' + ('using predicted values' if predictive else 'using observed values') +
                f" / coverage {Time(first, format='mjd').iso[:10]} ～ {Time(last, format='mjd').iso[:10]}" +
                '\nSource: ' + str(source))
