FROM python:3.11-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg \
    FLET_FORCE_WEB_SERVER=true FLET_SERVER_PORT=8000 \
    XDG_CACHE_HOME=/opt/sked-cache MPLCONFIGDIR=/tmp/sked-matplotlib \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
COPY antenna.sch vlbacoord.pickle vlbacalib_allfreq_full2023a_thresh.npy ./
COPY template/ ./template/
COPY assets/ ./assets/
RUN useradd --create-home --uid 10001 sked \
    && mkdir -p /opt/sked-cache/astropy \
    && chown -R sked:sked /opt/sked-cache
USER sked
# Baked into the image: available again after every cold start.
# To refresh unchanged builds on Render, use Clear build cache & deploy.
RUN python prepare_iers_cache.py
EXPOSE 8000
CMD ["python", "schedule_app.py"]
