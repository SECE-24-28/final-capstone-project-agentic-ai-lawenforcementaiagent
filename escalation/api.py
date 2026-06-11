from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
from .db import init_db, SessionLocal
from .dashboard import router as dashboard_router
from .models import Escalation, AdvocateProfile
from .scheduler import fire_alerts, schedule_retries, start, stop
from datetime import datetime
from typing import Optional
from .scheduler import sched

router = APIRouter(tags=["escalations"])
router.include_router(dashboard_router)


class EscalationIn(BaseModel):
    case_id: str
    event_type: str
    urgency: str
    advocate_id: str
    lawyer_name: Optional[str] = None
    lawyer_whatsapp_number: Optional[str] = None
    lawyer_phone: Optional[str] = None
    lawyer_email: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    client_whatsapp_number: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    event_summary: Optional[str] = None
    case_history: Optional[dict] = None
    drafter_notes: Optional[str] = None
    deadline: Optional[str] = None


class AckIn(BaseModel):
    acknowledged_by: str


class ResolveIn(BaseModel):
    resolution_notes: Optional[str] = None


def start_escalation_service():
    init_db()
    start()


def stop_escalation_service():
    stop()


@router.post("/escalate")
def escalate(payload: EscalationIn):
    brief = _build_case_brief(payload)

    db = SessionLocal()

    # ensure advocate exists (for demo create a default profile if missing)
    adv = db.query(AdvocateProfile).filter(AdvocateProfile.advocate_id == payload.advocate_id).first()
    if not adv:
        adv = AdvocateProfile(
            advocate_id=payload.advocate_id,
            name=payload.lawyer_name or payload.advocate_id,
            whatsapp_number=payload.lawyer_whatsapp_number,
            phone_number=payload.lawyer_phone,
            email=payload.lawyer_email,
            push_token=None,
            quiet_hours_start="23:00",
            quiet_hours_end="06:00",
        )
        db.add(adv)
        db.commit()
    else:
        adv.name = payload.lawyer_name or adv.name
        adv.whatsapp_number = (
            payload.lawyer_whatsapp_number or adv.whatsapp_number
        )
        adv.phone_number = payload.lawyer_phone or adv.phone_number
        adv.email = payload.lawyer_email or adv.email
        db.commit()

    esc = Escalation(
        case_id=payload.case_id,
        advocate_id=payload.advocate_id,
        event_type=payload.event_type,
        urgency_level=payload.urgency,
        brief=brief,
        client_id=payload.client_id,
        client_name=payload.client_name,
        client_whatsapp_number=payload.client_whatsapp_number,
        client_phone=payload.client_phone,
        client_email=payload.client_email,
        brief_prepared_at=datetime.utcnow(),
        total_alerts_sent=0,
    )
    db.add(esc)
    db.commit()
    db.refresh(esc)

    # Quiet hours handling
    adv = db.query(AdvocateProfile).filter(AdvocateProfile.advocate_id == payload.advocate_id).first()
    now = datetime.utcnow()
    fire_now = True
    if adv and adv.quiet_hours_start and adv.quiet_hours_end and payload.urgency == "HIGH":
        # parse HH:MM
        try:
            qs_h, qs_m = map(int, adv.quiet_hours_start.split(":"))
            qe_h, qe_m = map(int, adv.quiet_hours_end.split(":"))
            from datetime import time as dtime
            qs = dtime(qs_h, qs_m)
            qe = dtime(qe_h, qe_m)
            now_local = datetime.utcnow().time()
            in_quiet = False
            if qs < qe:
                in_quiet = qs <= now_local <= qe
            else:
                # overnight
                in_quiet = now_local >= qs or now_local <= qe

            if in_quiet:
                fire_now = False
        except Exception:
            fire_now = True

    # Fire immediately for CRITICAL or if not in quiet hours
    if payload.urgency == "CRITICAL" or fire_now:
        fire_alerts(esc.escalation_id)

    # Decide retry interval based on urgency
    if payload.urgency == "CRITICAL":
        interval = 15
    elif payload.urgency == "HIGH":
        interval = 30
    else:
        interval = 0

    if interval > 0:
        schedule_retries(esc.escalation_id, interval_minutes=interval)

    db.close()

    return {"status": "escalation_created", "escalation_id": esc.escalation_id, "brief": brief}


def _build_case_brief(payload: EscalationIn) -> str:
    history = payload.case_history or {}
    history_text = "\n".join(
        f"- {key.replace('_', ' ').title()}: {value}"
        for key, value in history.items()
    )
    sections = [
        f"{payload.urgency} ALERT - Case {payload.case_id}",
        f"Event: {payload.event_summary or payload.event_type}",
        f"Deadline: {payload.deadline or 'Not provided'}",
    ]
    if history_text:
        sections.append(f"Case history:\n{history_text}")
    if payload.drafter_notes:
        sections.append(f"Notes: {payload.drafter_notes}")
    return "\n\n".join(sections)


@router.post("/escalation/{escalation_id}/ack")
def acknowledge(escalation_id: int, payload: AckIn):
    db = SessionLocal()
    esc = db.query(Escalation).filter(Escalation.escalation_id == escalation_id).first()
    if not esc:
        db.close()
        raise HTTPException(status_code=404, detail="Escalation not found")

    esc.acknowledgement_received_at = datetime.utcnow()
    esc.acknowledged_by = payload.acknowledged_by
    db.add(esc)
    db.commit()

    # remove scheduler job if exists
    job_id = f"escalation_retry_{escalation_id}"
    try:
        sched.remove_job(job_id)
    except Exception:
        pass

    db.close()
    return {"status": "acknowledged", "escalation_id": escalation_id}


@router.post("/escalation/{escalation_id}/resolve")
def resolve(escalation_id: int, payload: ResolveIn):
    db = SessionLocal()
    esc = db.query(Escalation).filter(Escalation.escalation_id == escalation_id).first()
    if not esc:
        db.close()
        raise HTTPException(status_code=404, detail="Escalation not found")

    esc.resolved_at = datetime.utcnow()
    esc.resolution_notes = payload.resolution_notes
    db.add(esc)
    db.commit()
    db.close()
    return {"status": "resolved", "escalation_id": escalation_id}


def create_app() -> FastAPI:
    standalone_app = FastAPI(title="Escalation Agent")
    standalone_app.include_router(router)
    standalone_app.add_event_handler("startup", start_escalation_service)
    standalone_app.add_event_handler("shutdown", stop_escalation_service)
    return standalone_app


# Standalone entry point: uvicorn escalation.api:app
app = create_app()
