from fastapi import FastAPI
from fastapi.testclient import TestClient

from escalation import (
    escalation_router,
    start_escalation_service,
    stop_escalation_service,
)


def test_router_can_be_mounted_in_main_application():
    main_app = FastAPI()
    main_app.include_router(escalation_router, prefix="/api")
    main_app.add_event_handler("startup", start_escalation_service)
    main_app.add_event_handler("shutdown", stop_escalation_service)

    with TestClient(main_app) as client:
        response = client.post(
            "/api/escalate",
            json={
                "case_id": "MAIN-APP-001",
                "event_type": "HEARING_UPDATED",
                "urgency": "NORMAL",
                "advocate_id": "ADV-001",
                "event_summary": "The next hearing date was updated.",
            },
        )
        dashboard = client.get("/api/dashboard")
        summary = client.get("/api/dashboard/summary")
        records = client.get(
            "/api/dashboard/escalations",
            params={"search": "MAIN-APP-001"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "escalation_created"
    assert dashboard.status_code == 200
    assert "Escalation command center" in dashboard.text
    assert summary.status_code == 200
    assert summary.json()["total"] >= 1
    assert records.status_code == 200
    assert records.json()["items"][0]["case_id"] == "MAIN-APP-001"
