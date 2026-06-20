from django.conf import settings


def demo_mode(request):
    """Expose DEMO_MODE to templates (drives the login demo banner/prefill)."""
    return {"demo_mode": settings.DEMO_MODE}


def unread_notifications(request):
    """Expose the current user's unread notification count to the nav."""
    if not request.user.is_authenticated:
        return {"unread_notifications": 0}
    from apps.tickets.models import Notification

    return {
        "unread_notifications": Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    }
