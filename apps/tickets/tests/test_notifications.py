from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.tickets.choices import Priority, Status
from apps.tickets.models import Notification, Ticket
from apps.tickets.tests.factories import TicketFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_assign_notifies_assignee():
    ticket = TicketFactory()
    agent = UserFactory(username="agent-x")
    ticket.assign_to(agent, actor=None)
    assert Notification.objects.filter(user=agent, ticket=ticket).exists()


def test_comment_notifies_assignee():
    assignee = UserFactory(username="assignee-x")
    ticket = TicketFactory(assignee=assignee)
    ticket.comments.create(author=ticket.requester, body="any update?")
    assert Notification.objects.filter(user=assignee, ticket=ticket).exists()


def test_sla_sweep_marks_breach_escalates_and_notifies():
    assignee = UserFactory(username="oncall")
    assignee.email = "oncall@example.com"
    assignee.save()
    ticket = TicketFactory(
        assignee=assignee, status=Status.IN_PROGRESS, priority=Priority.P3_NORMAL
    )
    Ticket.objects.filter(pk=ticket.pk).update(
        sla_due_at=timezone.now() - timedelta(hours=1), sla_breached=False
    )

    call_command("sla_sweep")

    ticket.refresh_from_db()
    assert ticket.sla_breached is True
    assert ticket.priority == Priority.P2_HIGH  # escalated one level
    assert Notification.objects.filter(user=assignee, ticket=ticket).exists()
    assert any(ticket.key in m.subject for m in mail.outbox)


def test_sla_sweep_is_idempotent():
    ticket = TicketFactory(status=Status.IN_PROGRESS)
    Ticket.objects.filter(pk=ticket.pk).update(
        sla_due_at=timezone.now() - timedelta(hours=1), sla_breached=False
    )
    call_command("sla_sweep")
    count_after_first = Notification.objects.count()
    call_command("sla_sweep")
    assert Notification.objects.count() == count_after_first  # no duplicate alerts


def test_notifications_view_marks_read(client, agent_user):
    Notification.objects.create(user=agent_user, ticket=None, text="hello")
    client.force_login(agent_user)
    response = client.get("/notifications/")
    assert response.status_code == 200
    assert Notification.objects.filter(user=agent_user, is_read=False).count() == 0
