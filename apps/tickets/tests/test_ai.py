import pytest

from apps.tickets.ai import draft_reply, suggest_triage, summarize_ticket
from apps.tickets.tests.factories import TicketFactory

pytestmark = pytest.mark.django_db


def test_suggest_triage_matches_keywords():
    result = suggest_triage("VPN keeps disconnecting", "")
    assert result["source"] == "mock"
    assert result["category"] == "Network"
    assert result["priority"]


def test_suggest_triage_defaults_when_no_signal():
    result = suggest_triage("Hmm something", "")
    assert result["source"] == "mock"
    assert result["priority"] == "p3_normal"


def test_summarize_ticket_mock_mentions_key():
    ticket = TicketFactory()
    result = summarize_ticket(ticket)
    assert result["source"] == "mock"
    assert ticket.key in result["text"]


def test_draft_reply_mock_nonempty():
    ticket = TicketFactory()
    result = draft_reply(ticket)
    assert result["source"] == "mock"
    assert result["text"]


def test_api_ai_summarize_for_agent(api_client, agent_user):
    ticket = TicketFactory()
    api_client.force_authenticate(agent_user)
    response = api_client.post(f"/api/tickets/{ticket.id}/ai/summarize/")
    assert response.status_code == 200
    assert response.data["source"] == "mock"


def test_api_ai_triage_for_agent(api_client, agent_user):
    ticket = TicketFactory(title="Printer is jammed again")
    api_client.force_authenticate(agent_user)
    response = api_client.post(f"/api/tickets/{ticket.id}/ai/triage/")
    assert response.status_code == 200
    assert "priority" in response.data


def test_api_ai_forbidden_for_requester(api_client, requester_user):
    ticket = TicketFactory(requester=requester_user)
    api_client.force_authenticate(requester_user)
    assert api_client.post(f"/api/tickets/{ticket.id}/ai/summarize/").status_code == 403


def test_standalone_triage_endpoint(api_client, agent_user):
    api_client.force_authenticate(agent_user)
    response = api_client.post(
        "/api/ai/triage/", {"title": "Reset my password", "description": ""}, format="json"
    )
    assert response.status_code == 200
    assert response.data["category"] == "Access"


def test_detail_ai_summary_renders(client, agent_user):
    ticket = TicketFactory()
    client.force_login(agent_user)
    response = client.post(f"/tickets/{ticket.key}/", {"action": "ai_summary"})
    assert response.status_code == 200
    assert b"Summary" in response.content
