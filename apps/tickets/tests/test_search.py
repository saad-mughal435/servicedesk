import pytest

from apps.tickets.models import Ticket
from apps.tickets.search import search_tickets
from apps.tickets.tests.factories import TicketFactory

pytestmark = pytest.mark.django_db


def test_search_filters_by_title():
    TicketFactory(title="VPN keeps dropping")
    TicketFactory(title="Printer jam on floor 3")
    results = search_tickets(Ticket.objects.all(), "vpn")
    assert results.count() == 1
    assert "VPN" in results.first().title


def test_search_empty_returns_all():
    TicketFactory()
    TicketFactory()
    assert search_tickets(Ticket.objects.all(), "").count() == 2


def test_search_matches_key():
    ticket = TicketFactory()
    assert ticket in list(search_tickets(Ticket.objects.all(), ticket.key))


def test_api_search_q(api_client, agent_user):
    TicketFactory(title="Email outage in finance")
    TicketFactory(title="New laptop request")
    api_client.force_authenticate(agent_user)
    response = api_client.get("/api/tickets/", {"q": "outage"})
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_ui_search_q(client, agent_user):
    TicketFactory(title="Wifi down in warehouse")
    TicketFactory(title="Monitor replacement")
    client.force_login(agent_user)
    response = client.get("/tickets/", {"q": "wifi"})
    assert response.status_code == 200
    assert b"Wifi down" in response.content
    assert b"Monitor replacement" not in response.content
