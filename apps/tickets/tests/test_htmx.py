import pytest

from apps.tickets.tests.factories import TicketFactory

pytestmark = pytest.mark.django_db


def test_board_hx_returns_rows_partial(client, agent_user):
    TicketFactory()
    client.force_login(agent_user)
    response = client.get("/tickets/", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert b'id="ticket-rows"' in response.content
    assert b"<html" not in response.content  # partial, not the full page


def test_board_full_page_without_hx(client, agent_user):
    client.force_login(agent_user)
    response = client.get("/tickets/")
    assert b"<html" in response.content


def test_comment_hx_returns_comment_list(client, agent_user):
    ticket = TicketFactory()
    client.force_login(agent_user)
    response = client.post(
        f"/tickets/{ticket.key}/",
        {"action": "comment", "body": "htmx note"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert b"htmx note" in response.content
    assert b'id="comment-list"' in response.content
    assert b"<html" not in response.content


def test_comment_without_hx_redirects(client, agent_user):
    ticket = TicketFactory()
    client.force_login(agent_user)
    response = client.post(
        f"/tickets/{ticket.key}/", {"action": "comment", "body": "normal note"}
    )
    assert response.status_code == 302
