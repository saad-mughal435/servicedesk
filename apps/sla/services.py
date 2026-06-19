"""SLA timing logic.

The pure ``resolution_due`` function is the unit-test centerpiece; ``due_for``
resolves the active policy for a priority and applies it.
"""

from datetime import datetime, timedelta


def resolution_due(start: datetime, resolution_minutes: int) -> datetime:
    """Return when resolution is due given a start time and an SLA budget."""
    return start + timedelta(minutes=resolution_minutes)


def due_for(start: datetime, priority: str) -> datetime | None:
    """Resolve the active SLA policy for ``priority`` and return its due time.

    Falls back to the default policy; returns ``None`` if neither exists.
    """
    from apps.sla.models import SlaPolicy

    policy = SlaPolicy.for_priority(priority)
    if policy is None:
        return None
    return resolution_due(start, policy.resolution_minutes)
