"""Fetch and validate the IERS-A cache while building the deployment image."""
from astropy.time import Time
from astropy.utils import iers
from astropy.utils.data import download_file


def prepare_cache():
    # Use the canonical URL as cache key even if the mirror supplies the file.
    # Fail the build rather than silently shipping an offline fallback.
    filename = download_file(
        iers.conf.iers_auto_url, cache='update', timeout=60,
        sources=[iers.conf.iers_auto_url, iers.conf.iers_auto_url_mirror])
    table = iers.IERS_Auto.read(filename)
    age = Time.now().mjd - table.meta['predictive_mjd']
    if age > 30:
        raise RuntimeError(f'Downloaded IERS predictions are too old ({age:.1f} days).')
    print(f'IERS cache ready: prediction age {age:.1f} days; '
          f'coverage through MJD {table["MJD"][-1].value:.0f}')


if __name__ == '__main__':
    prepare_cache()
