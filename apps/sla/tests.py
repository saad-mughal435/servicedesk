from datetime import UTC, datetime

import pytest

from apps.sla.models import SlaPolicy
from apps.sla.services import due_for, resolution_due
from apps.tickets.choices import Priority

START = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)


def test_resolution_due_adds_minutes():
    assert resolution_due(START, 240) == datetime(2026, 6, 1, 13, 0, tzinfo=UTC)


@pytest.mark.django_db
def test_due_for_uses_matching_active_policy():
    SlaPolicy.objects.create(
        name="Critical", priority=Priority.P1_CRITICAL, response_minutes=30, resolution_minutes=240
    )
    assert due_for(START, Priority.P1_CRITICAL) == datetime(
        2026, 6, 1, 13, 0, tzinfo=UTC
    )


@pytest.mark.django_db
def test_due_for_falls_back_to_default_policy():
    SlaPolicy.objects.create(
        name="Standard",
        priority=Priority.P3_NORMAL,
        response_minutes=120,
        resolution_minutes=1440,
        is_default=True,
    )
    # No policy for P4 -> default (P3) applies.
    assert due_for(START, Priority.P4_LOW) == resolution_due(START, 1440)


@pytest.mark.django_db
def test_for_priority_returns_none_when_no_policies():
    assert SlaPolicy.for_priority(Priority.P1_CRITICAL) is None
    assert due_for(START, Priority.P1_CRITICAL) is None
