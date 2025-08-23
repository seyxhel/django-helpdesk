from django.http import JsonResponse


def healthz(request):
    """Simple health endpoint for load balancers / health checks."""
    return JsonResponse({"status": "ok"})
