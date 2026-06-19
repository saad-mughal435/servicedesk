import pytest

from apps.tickets.models import Comment
from apps.tickets.tests.factories import TicketFactory

pytestmark = pytest.mark.django_db


def test_dashboard_redirects_anonymous(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_dashboard_ok_for_agent(client, agent_user):
    client.force_login(agent_user)
    assert client.get("/").status_code == 200


def test_ticket_list_ok_for_agent(client, agent_user):
    TicketFactory()
    client.force_login(agent_user)
    assert client.get("/tickets/").status_code == 200


def test_ticket_detail_and_comment_post(client, agent_user):
    ticket = TicketFactory()
    client.force_login(agent_user)
    assert client.get(f"/tickets/{ticket.key}/").status_code == 200
    response = client.post(
        f"/tickets/{ticket.key}/", {"action": "comment", "body": "on it"}
    )
    assert response.status_code == 302
    assert Comment.objects.filter(ticket=ticket, body="on it").exists()


def test_requester_cannot_open_others_ticket(client, requester_user):
    ticket = TicketFactory()  # belongs to someone else
    client.force_login(requester_user)
    assert client.get(f"/tickets/{ticket.key}/").status_code == 404
