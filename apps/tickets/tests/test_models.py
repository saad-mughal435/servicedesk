from datetime import timedelta

import pytest
from django.utils import timezone

from apps.sla.models import SlaPolicy
from apps.tickets.choices import EventVerb, Priority, Status, TicketType
from apps.tickets.models import Comment, Ticket
from apps.tickets.tests.factories import TicketFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def p1_policy():
    return SlaPolicy.objects.create(
        name="Critical",
        priority=Priority.P1_CRITICAL,
        response_minutes=30,
        resolution_minutes=240,
    )


def test_incident_gets_inc_key():
    ticket = TicketFactory(ticket_type=TicketType.INCIDENT)
    assert ticket.key.startswith("INC-")


def test_service_request_gets_sr_key():
    ticket = TicketFactory(ticket_type=TicketType.SERVICE_REQUEST)
    assert ticket.key.startswith("SR-")


def test_save_applies_matching_sla_policy(p1_policy):
    ticket = TicketFactory(priority=Priority.P1_CRITICAL)
    assert ticket.sla_policy_id == p1_policy.id
    assert ticket.sla_due_at is not None


def test_created_event_logged_once():
    ticket = TicketFactory()
    assert ticket.events.filter(verb=EventVerb.CREATED).count() == 1


def test_assign_to_sets_assignee_status_and_event():
    ticket = TicketFactory()
    agent = UserFactory(username="a1")
    ticket.assign_to(agent, actor=agent)
    ticket.refresh_from_db()
    assert ticket.assignee == agent
    assert ticket.status == Status.ASSIGNED
    assert ticket.events.filter(verb=EventVerb.ASSIGNED).exists()


def test_mark_resolved_sets_timestamp_and_event():
    ticket = TicketFactory()
    ticket.mark_resolved()
    ticket.refresh_from_db()
    assert ticket.status == Status.RESOLVED
    assert ticket.resolved_at is not None
    assert ticket.events.filter(verb=EventVerb.RESOLVED).exists()
    assert ticket.is_open is False


def test_sla_breached_when_overdue_and_open(p1_policy):
    ticket = TicketFactory(priority=Priority.P1_CRITICAL)
    Ticket.objects.filter(pk=ticket.pk).update(
        sla_due_at=timezone.now() - timedelta(hours=1)
    )
    ticket.refresh_from_db()
    assert ticket.evaluate_sla() is True


def test_sla_not_breached_when_due_in_future(p1_policy):
    ticket = TicketFactory(priority=Priority.P1_CRITICAL)
    assert ticket.sla_due_at > timezone.now()
    assert ticket.evaluate_sla() is False


def test_comment_signal_logs_event():
    ticket = TicketFactory()
    Comment.objects.create(ticket=ticket, author=ticket.requester, body="looking into it")
    assert ticket.events.filter(verb=EventVerb.COMMENTED).count() == 1
