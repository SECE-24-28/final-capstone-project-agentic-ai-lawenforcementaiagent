from fastapi.testclient import TestClient
from escalation.api import app


def test_create_escalation():
    payload = {
        "case_id": "OS234/2024",
        "event_type": "CONTEMPT_PETITION_FILED",
        "urgency": "CRITICAL",
        "advocate_id": "ADV_RAJAN_001",
        "lawyer_name": "Advocate Rajan",
        "lawyer_whatsapp_number": "+919900000001",
        "lawyer_phone": "+919900000001",
        "lawyer_email": "rajan@example.com",
        "client_id": "CLIENT_001",
        "client_name": "Client One",
        "client_whatsapp_number": "+919900000002",
        "client_phone": "+919900000002",
        "client_email": "client@example.com",
        "event_summary": "Opponent filed contempt petition at 11:47PM",
        "deadline": "Court may take up tomorrow morning",
        "case_history": {"last_hearing": "10 June 2026"},
        "drafter_notes": "Review the contempt filing before court."
    }

    with TestClient(app) as client:
        resp = client.post("/escalate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "escalation_created"
    assert "escalation_id" in data
    assert "Opponent filed contempt petition" in data["brief"]
    assert "Last Hearing: 10 June 2026" in data["brief"]
