from fastapi.testclient import TestClient

from escalation.api import app


def test_dashboard_actions_update_status():
    with TestClient(app) as client:
        created = client.post(
            "/escalate",
            json={
                "case_id": "DASHBOARD-001",
                "event_type": "URGENT_FILING",
                "urgency": "NORMAL",
                "advocate_id": "ADV-DASHBOARD",
            },
        ).json()
        escalation_id = created["escalation_id"]

        acknowledged = client.post(
            f"/escalation/{escalation_id}/ack",
            json={"acknowledged_by": "Dashboard User"},
        )
        after_ack = client.get(
            "/dashboard/escalations",
            params={"search": "DASHBOARD-001"},
        ).json()["items"][0]

        resolved = client.post(
            f"/escalation/{escalation_id}/resolve",
            json={"resolution_notes": "Handled in the main application."},
        )
        after_resolve = client.get(
            "/dashboard/escalations",
            params={"search": "DASHBOARD-001"},
        ).json()["items"][0]

    assert acknowledged.status_code == 200
    assert after_ack["status"] == "acknowledged"
    assert resolved.status_code == 200
    assert after_resolve["status"] == "resolved"
