# Aggregate Prometheus metrics across gunicorn workers: when a worker exits, mark
# its multiprocess metric files dead so /metrics doesn't double-count it.
import os

from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics

# Create the multiprocess dir at master startup (before workers fork). The root
# filesystem is read-only in-cluster, so this path is an emptyDir mount on /tmp.
os.makedirs(os.environ["PROMETHEUS_MULTIPROC_DIR"], exist_ok=True)


def child_exit(server, worker):
    GunicornPrometheusMetrics.mark_process_dead(worker.pid)
