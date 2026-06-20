import pytest

from apps.tickets.metrics import compute_metrics
from apps.tickets.tests.factories import TicketFactory

pytestmark = pytest.mark.django_db


def test_compute_metrics_shape():
    TicketFactory()
    m = compute_metrics()
    assert {
        "totals",
        "sla_compliance_pct",
        "avg_resolution_hours",
        "by_status",
        "by_priority",
        "volume_14d",
        "top_categories",
    } <= set(m)
    assert len(m["volume_14d"]) == 14
    assert m["totals"]["all"] == 1


def test_metrics_api_requires_auth(api_client):
    assert api_client.get("/api/metrics/").status_code in (401, 403)


def test_metrics_api_ok_for_agent(api_client, agent_user):
    api_client.force_authenticate(agent_user)
    response = api_client.get("/api/metrics/")
    assert response.status_code == 200
    assert "sla_compliance_pct" in response.data


def test_reports_page_ok_for_agent(client, agent_user):
    client.force_login(agent_user)
    assert client.get("/reports/").status_code == 200


def test_reports_redirects_requester(client, requester_user):
    client.force_login(requester_user)
    assert client.get("/reports/").status_code == 302


def test_healthz_ok(client):
    assert client.get("/healthz").status_code == 200


def test_readyz_ok(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
