from django.conf import settings


def demo_mode(request):
    """Expose DEMO_MODE to templates (drives the login demo banner/prefill)."""
    return {"demo_mode": settings.DEMO_MODE}
