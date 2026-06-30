# Aggregate Prometheus metrics across gunicorn workers: when a worker exits, mark
# its multiprocess metric files dead so /metrics doesn't double-count it.
from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics


def child_exit(server, worker):
    GunicornPrometheusMetrics.mark_process_dead(worker.pid)
