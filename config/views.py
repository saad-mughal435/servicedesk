"""Infrastructure endpoints: liveness and readiness probes."""

from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Liveness — the process is up."""
    return JsonResponse({"status": "ok"})


def readyz(request):
    """Readiness — the database is reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ready"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
