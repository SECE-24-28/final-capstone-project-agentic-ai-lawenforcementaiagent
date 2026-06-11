# Escalation Agent (minimal)

This is a minimal, runnable Escalation Agent for VakilAgent.

What it includes:
- FastAPI service exposing an endpoint to receive escalation triggers
- SQLAlchemy models for `escalations` and `advocate_profiles`
- Twilio notifications for WhatsApp and SMS
- SendGrid email notifications
- Lawyer and client notifications using contact details supplied by the main app
- APScheduler-based retry logic to resend alerts every X minutes
- Simple in-memory SQLite by default; can be pointed to PostgreSQL via DATABASE_URL
- Tests using pytest

Run locally:

1. Create a virtualenv and install deps
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt

2. Start the API:
   uvicorn escalation.api:app --reload

3. POST to /escalate with a JSON payload (example in tests)

Example request:

```json
{
  "case_id": "OS234/2024",
  "event_type": "CONTEMPT_PETITION_FILED",
  "urgency": "CRITICAL",
  "advocate_id": "ADV_RAJAN_001",
  "lawyer_phone": "+919900000001",
  "lawyer_whatsapp_number": "+919900000001",
  "lawyer_email": "lawyer@example.com",
  "client_id": "CLIENT_001",
  "client_phone": "+919900000002",
  "client_whatsapp_number": "+919900000002",
  "client_email": "client@example.com",
  "event_summary": "Opponent filed a contempt petition",
  "deadline": "Court may take up the matter tomorrow morning",
  "case_history": {"last_hearing": "10 June 2026"},
  "drafter_notes": "Review the filing before court."
}
```

Configuration:

1. Copy `.env.example` to `.env`.
2. Add Twilio and SendGrid credentials.
3. Set `ENABLE_EXTERNAL_NOTIFICATIONS=true` only when real messages should
   be sent.

The case brief is generated locally from the event summary, deadline, case
history, and drafter notes. It does not require an AI API.

## Integrate into a FastAPI application

Copy the `escalation` package into the main application's source tree, or
install this repository as a package. Then register its router and lifecycle
handlers in the main FastAPI application:

```python
from fastapi import FastAPI

from escalation import (
    escalation_router,
    start_escalation_service,
    stop_escalation_service,
)

app = FastAPI()

app.include_router(escalation_router, prefix="/api")
app.add_event_handler("startup", start_escalation_service)
app.add_event_handler("shutdown", stop_escalation_service)
```

The resulting endpoints are:

- `POST /api/escalate`
- `POST /api/escalation/{escalation_id}/ack`
- `POST /api/escalation/{escalation_id}/resolve`
- `GET /api/dashboard`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/escalations`

Open `/api/dashboard` in a browser to view counts, filter escalations, and
acknowledge or resolve records. The dashboard refreshes automatically every
30 seconds and requires no separate frontend build.

The main application should provide lawyer and client contact details in the
`/api/escalate` request. Put the Twilio, SendGrid, and database variables in
the main application's environment configuration.

For production, point `DATABASE_URL` at the main PostgreSQL database and add
the escalation tables through the main application's migration system.
`Base.metadata.create_all()` is suitable for local setup, but it does not
replace Alembic or another production migration tool.

Run only one APScheduler instance. If the main application runs multiple
workers or containers, move retry jobs to the application's existing task
queue, such as Celery, RQ, or a dedicated scheduler process.
