from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError


def healthz(request):
    """Health endpoint that performs a quick DB connectivity check.

    Returns 200 with {status: 'ok', db: 'ok'} when database is reachable.
    Returns 200 with {status: 'ok', db: 'unreachable'} if DB is not configured
    (e.g. read-only static setups), or 503 when DB exists but query fails.
    """
    # Default response
    result = {"status": "ok"}

    # Attempt a lightweight DB check on the default DB.
    try:
        conn = connections['default']
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        result['db'] = 'ok'
        return JsonResponse(result, status=200)
    except (OperationalError, Exception) as e:
        # If there's no DB configured, surface it as unreachable but keep 200
        # for static-only deployments. If the DB is expected and failing, return 503.
        # Heuristic: if DATABASE_URL / POSTGRES_HOST env exists, treat as expected.
        db_env = any(
            [
                bool(os.environ.get('DATABASE_URL')),
                bool(os.environ.get('POSTGRES_HOST')),
                bool(os.environ.get('POSTGRES_DB')),
            ]
        )
        result['db'] = 'unreachable'
        result['error'] = str(e)
        return JsonResponse(result, status=(200 if not db_env else 503))
