# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Runner (Final Image)
# ==========================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY --chown=appuser:appuser app.py db.py gunicorn.conf.py ./
COPY --chown=appuser:appuser services/ ./services/
# load_seed.py + seed_pool.csv ship in the image so the Helm post-install Job
# can seed the dataset without mounting the 573 MB source.
COPY --chown=appuser:appuser scripts/ ./scripts/

ENV PATH="/opt/venv/bin:$PATH"

# Prometheus multiprocess metrics: gunicorn workers write per-process db files
# here, so the dir must exist and be writable by the runtime user.
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
RUN mkdir -p /tmp/prometheus_multiproc && chown appuser:appuser /tmp/prometheus_multiproc

# Numeric so K8s runAsNonRoot can verify the user is non-root
USER 1000:1000

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
