import pytest

from apps.tickets.choices import Priority, Status
from apps.tickets.models import Ticket
from apps.tickets.tests.factories import TicketFactory

pytestmark = pytest.mark.django_db

API = "/api/tickets/"


def test_anonymous_is_rejected(api_client):
    assert api_client.get(API).status_code in (401, 403)


def test_agent_lists_all_tickets(api_client, agent_user):
    TicketFactory()
    TicketFactory()
    api_client.force_authenticate(agent_user)
    response = api_client.get(API)
    assert response.status_code == 200
    assert response.data["count"] == 2


def test_requester_sees_only_their_own(api_client, requester_user):
    own = TicketFactory(requester=requester_user)
    TicketFactory()  # belongs to someone else
    api_client.force_authenticate(requester_user)
    response = api_client.get(API)
    assert response.data["count"] == 1
    assert response.data["results"][0]["key"] == own.key


def test_requester_can_create_ticket(api_client, requester_user):
    api_client.force_authenticate(requester_user)
    response = api_client.post(
        API,
        {"title": "Need help", "priority": Priority.P3_NORMAL, "ticket_type": "incident"},
        format="json",
    )
    assert response.status_code == 201
    assert Ticket.objects.get(key=response.data["key"]).requester == requester_user


def test_requester_cannot_resolve(api_client, requester_user):
    ticket = TicketFactory(requester=requester_user)
    api_client.force_authenticate(requester_user)
    assert api_client.post(f"{API}{ticket.id}/resolve/").status_code == 403


def test_agent_can_assign_and_logs_event(api_client, agent_user):
    ticket = TicketFactory()
    api_client.force_authenticate(agent_user)
    response = api_client.post(
        f"{API}{ticket.id}/assign/", {"assignee": agent_user.id}, format="json"
    )
    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.assignee == agent_user
    assert ticket.events.filter(verb="assigned").exists()


def test_agent_can_resolve(api_client, agent_user):
    ticket = TicketFactory()
    api_client.force_authenticate(agent_user)
    response = api_client.post(f"{API}{ticket.id}/resolve/")
    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.status == Status.RESOLVED


def test_filter_by_status(api_client, agent_user):
    TicketFactory(status=Status.NEW)
    TicketFactory(status=Status.RESOLVED)
    api_client.force_authenticate(agent_user)
    response = api_client.get(API, {"status": Status.RESOLVED})
    assert response.data["count"] == 1


def test_pagination_envelope(api_client, agent_user):
    TicketFactory()
    api_client.force_authenticate(agent_user)
    response = api_client.get(API)
    assert {"count", "next", "previous", "results"} <= set(response.data.keys())


def test_comments_action_post_then_get(api_client, agent_user):
    ticket = TicketFactory()
    api_client.force_authenticate(agent_user)
    posted = api_client.post(
        f"{API}{ticket.id}/comments/", {"body": "working on it"}, format="json"
    )
    assert posted.status_code == 201
    listed = api_client.get(f"{API}{ticket.id}/comments/")
    assert listed.status_code == 200
    assert len(listed.data) == 1


def test_demo_mode_blocks_delete(api_client, manager_user, settings):
    settings.DEMO_MODE = True
    ticket = TicketFactory()
    api_client.force_authenticate(manager_user)
    assert api_client.delete(f"{API}{ticket.id}/").status_code == 403


def test_manager_can_delete_when_not_demo(api_client, manager_user, settings):
    settings.DEMO_MODE = False
    ticket = TicketFactory()
    api_client.force_authenticate(manager_user)
    assert api_client.delete(f"{API}{ticket.id}/").status_code == 204


def test_agent_cannot_delete(api_client, agent_user, settings):
    settings.DEMO_MODE = False
    ticket = TicketFactory()
    api_client.force_authenticate(agent_user)
    assert api_client.delete(f"{API}{ticket.id}/").status_code == 403


def test_schema_is_public(api_client):
    assert api_client.get("/api/schema/").status_code == 200
