"""Small compatibility helpers shared by the two editors."""
from astropy.coordinates import SkyCoord
import astropy.units as u


def simbad_coordinate(table):
    if table is None or len(table) == 0:
        raise ValueError('SIMBADに天体が見つかりませんでした。')
    if 'ra' in table.colnames and 'dec' in table.colnames:
        return SkyCoord(float(table['ra'][0]) * u.deg, float(table['dec'][0]) * u.deg)
    return SkyCoord(str(table['RA'][0]), str(table['DEC'][0]), unit=(u.hourangle, u.deg))
