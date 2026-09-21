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
        raise ValueError('IERS確認にはスキャンが必要です。')
    times = Time([value.utc.mjd for scan in scans for value in (scan.start, scan.start + scan.dur)], format='mjd', scale='utc')
    with _LOCK:
        try:
            table = iers.IERS_Auto.open()
            # Without return_status, Astropy checks stale predictions and refreshes.
            table.ut1_utc(times)
            _, ut_status = table.ut1_utc(times, return_status=True)
            _, _, pm_status = table.pm_xy(times, return_status=True)
        except Exception as error:
            raise ValueError('IERSデータの取得・更新に失敗しました。ネット接続とデータの更新状況を確認してください。\n' + str(error)) from error
        if np.any(np.asarray(ut_status) < 0) or np.any(np.asarray(pm_status) < 0):
            raise ValueError('観測日時がIERSデータの収録範囲外です。検証結果は出せません。')
        first = float(table['MJD'][0].value)
        last = float(table['MJD'][-1].value)
        predictive = np.any(np.asarray(ut_status) == iers.FROM_IERS_A_PREDICTION) or np.any(np.asarray(pm_status) == iers.FROM_IERS_A_PREDICTION)
        source = table.meta.get('data_url', 'astropy-iers-data 同梱データ')
        return ('IERS: ' + ('予測値を使用' if predictive else '観測値を使用') +
                f" / 収録範囲 {Time(first, format='mjd').iso[:10]} ～ {Time(last, format='mjd').iso[:10]}" +
                '\n出典: ' + str(source))
