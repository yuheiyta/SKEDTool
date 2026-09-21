"""Read-only catalog cache and per-request search results."""
from functools import lru_cache
from pathlib import Path
import pickle
import numpy as np
import astropy.units as u


@lru_cache(maxsize=1)
def load_catalog():
    root = Path(__file__).resolve().parent
    with (root / 'vlbacoord.pickle').open('rb') as stream:
        coordinates = pickle.load(stream)
    table = np.load(root / 'vlbacalib_allfreq_full2023a_thresh.npy')
    table.setflags(write=False)
    return coordinates, table


def search_catalog(target, flux, minimum, maximum, expand=False):
    if not np.isfinite([flux, minimum, maximum]).all() or flux <= 0 or minimum < 0 or maximum <= minimum:
        raise ValueError('検索範囲とフラックス閾値に有効な正の値を指定してください。')
    coordinates, table = load_catalog()
    distance = target.separation(coordinates).deg
    for attempt in range(64):
        selected = np.where((distance >= minimum) & (distance <= maximum))[0]
        selected = selected[np.argsort(distance[selected])]
        rows = table[selected].copy()
        values = rows[:, 8:17].copy()
        values[(values == '--') | np.char.startswith(values, '<')] = 'nan'
        keep = (values.astype(float) > flux).any(axis=1)
        if keep.any():
            rows = rows[keep]
            separations = np.array([f'{value:.2f}' for value in distance[selected][keep]])
            message = f'Search: < {maximum:.1f} deg & > {int(flux * 1000)} mJy' if expand else f'Search: > {int(flux * 1000)} mJy'
            return message, np.insert(rows, 0, separations, axis=1)
        if not expand and not len(selected):
            break
        maximum = min(180.0, maximum * 1.5) if expand else maximum
        flux *= 0.75
    raise ValueError('条件に合う較正天体が見つかりませんでした。検索範囲を変更してください。')
