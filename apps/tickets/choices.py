"""Shared enumerations for the tickets domain.

Kept in a model-free module so other apps (e.g. ``sla``) can import the choices
without creating an app-loading import cycle.
"""

from django.db import models


class TicketType(models.TextChoices):
    INCIDENT = "incident", "Incident"
    SERVICE_REQUEST = "service_request", "Service request"


class Status(models.TextChoices):
    NEW = "new", "New"
    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In progress"
    ON_HOLD = "on_hold", "On hold"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


# Tickets in these states are no longer counted as "open" / actionable.
CLOSED_STATUSES = frozenset({Status.RESOLVED, Status.CLOSED, Status.CANCELLED})


class Priority(models.TextChoices):
    # Values sort lexicographically in priority order (p1 < p2 < p3 < p4).
    P1_CRITICAL = "p1_critical", "P1 - Critical"
    P2_HIGH = "p2_high", "P2 - High"
    P3_NORMAL = "p3_normal", "P3 - Normal"
    P4_LOW = "p4_low", "P4 - Low"


class EventVerb(models.TextChoices):
    CREATED = "created", "Created"
    ASSIGNED = "assigned", "Assigned"
    STATUS_CHANGED = "status_changed", "Status changed"
    PRIORITY_CHANGED = "priority_changed", "Priority changed"
    COMMENTED = "commented", "Commented"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"
    REOPENED = "reopened", "Reopened"
