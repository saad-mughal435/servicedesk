"""Operational analytics for the service desk dashboard and the metrics API."""

from datetime import timedelta

from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.tickets.choices import CLOSED_STATUSES, Priority, Status
from apps.tickets.models import Ticket

VOLUME_DAYS = 14


def compute_metrics() -> dict:
    """Return a JSON-serialisable snapshot of service-desk KPIs."""
    now = timezone.now()
    tickets = Ticket.objects.all()
    open_tickets = tickets.exclude(status__in=CLOSED_STATUSES)
    resolved = tickets.filter(resolved_at__isnull=False)

    total = tickets.count()
    total_resolved = resolved.count()

    # SLA compliance: resolved within the due time (no due = counted as met).
    met = resolved.filter(
        Q(sla_due_at__isnull=True) | Q(resolved_at__lte=F("sla_due_at"))
    ).count()
    compliance = round(100 * met / total_resolved, 1) if total_resolved else 100.0

    avg_delta = resolved.annotate(
        d=ExpressionWrapper(
            F("resolved_at") - F("created_at"), output_field=DurationField()
        )
    ).aggregate(a=Avg("d"))["a"]
    avg_resolution_hours = round(avg_delta.total_seconds() / 3600, 1) if avg_delta else 0.0

    status_counts = dict(
        tickets.values_list("status").annotate(n=Count("id")).values_list("status", "n")
    )
    by_status = [
        {"key": value, "label": label, "count": status_counts.get(value, 0)}
        for value, label in Status.choices
    ]

    priority_counts = dict(
        open_tickets.values_list("priority")
        .annotate(n=Count("id"))
        .values_list("priority", "n")
    )
    by_priority = [
        {"key": value, "label": label, "count": priority_counts.get(value, 0)}
        for value, label in Priority.choices
    ]

    # 14-day created-volume series, zero-filled.
    start_day = (now - timedelta(days=VOLUME_DAYS - 1)).date()
    raw = dict(
        tickets.filter(created_at__date__gte=start_day)
        .annotate(day=TruncDate("created_at"))
        .values_list("day")
        .annotate(n=Count("id"))
        .values_list("day", "n")
    )
    volume = [
        {
            "date": (start_day + timedelta(days=i)).isoformat(),
            "count": raw.get(start_day + timedelta(days=i), 0),
        }
        for i in range(VOLUME_DAYS)
    ]

    top_categories = [
        {"category": row["category__name"] or "Uncategorised", "count": row["n"]}
        for row in tickets.values("category__name")
        .annotate(n=Count("id"))
        .order_by("-n")[:6]
    ]

    return {
        "generated_at": now.isoformat(),
        "totals": {
            "all": total,
            "open": open_tickets.count(),
            "resolved": total_resolved,
            "breached": open_tickets.filter(sla_breached=True).count(),
        },
        "sla_compliance_pct": compliance,
        "avg_resolution_hours": avg_resolution_hours,
        "by_status": by_status,
        "by_priority": by_priority,
        "volume_14d": volume,
        "top_categories": top_categories,
    }
