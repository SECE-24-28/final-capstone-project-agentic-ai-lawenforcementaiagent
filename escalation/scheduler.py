import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from .db import SessionLocal
from .models import Escalation, AdvocateProfile
from .notifiers import send_push, send_whatsapp, send_sms, send_email, update_dashboard

logger = logging.getLogger("escalation.scheduler")

sched = BackgroundScheduler()


def _send_safely(channel: str, sender, *args, **kwargs):
    try:
        return sender(*args, **kwargs)
    except Exception:
        logger.exception("Failed to send escalation through %s", channel)
        return {"status": "failed", "channel": channel}


def fire_alerts(escalation_id: int):
    db = SessionLocal()
    esc = db.query(Escalation).filter(Escalation.escalation_id == escalation_id).first()
    if not esc:
        logger.error("Escalation not found: %s", escalation_id)
        db.close()
        return

    adv = db.query(AdvocateProfile).filter(AdvocateProfile.advocate_id == esc.advocate_id).first()

    brief = esc.brief or (
        f"{esc.event_type} - case {esc.case_id} - urgency {esc.urgency_level}"
    )
    subject = f"{esc.urgency_level} - Case {esc.case_id}"

    # Notify the assigned lawyer.
    if adv and adv.push_token:
        _send_safely(
            "push",
            send_push,
            adv.push_token,
            subject,
            brief,
            high_priority=(esc.urgency_level == "CRITICAL"),
        )
    if adv and adv.whatsapp_number:
        _send_safely("whatsapp", send_whatsapp, adv.whatsapp_number, brief)
    if adv and adv.phone_number:
        _send_safely("sms", send_sms, adv.phone_number, brief)
    if adv and adv.email:
        _send_safely(
            "email",
            send_email,
            adv.email,
            subject,
            brief,
            high_priority=(esc.urgency_level == "CRITICAL"),
        )

    # Notify the client through every contact channel supplied by the main app.
    if esc.client_whatsapp_number:
        _send_safely(
            "whatsapp", send_whatsapp, esc.client_whatsapp_number, brief
        )
    if esc.client_phone:
        _send_safely("sms", send_sms, esc.client_phone, brief)
    if esc.client_email:
        _send_safely(
            "email",
            send_email,
            esc.client_email,
            subject,
            brief,
            high_priority=(esc.urgency_level == "CRITICAL"),
        )
    if adv and adv.backup_contact_phone and esc.total_alerts_sent >= 3 and not esc.backup_contact_alerted:
        _send_safely(
            "backup_sms",
            send_sms,
            adv.backup_contact_phone,
            f"Urgent: Advocate {adv.name} has an escalation for case "
            f"{esc.case_id}. Please contact them immediately.",
        )
        esc.backup_contact_alerted = True

    # Dashboard always
    _send_safely(
        "dashboard",
        update_dashboard,
        esc.case_id,
        esc.urgency_level,
        brief,
    )

    # Update counters
    esc.channels_fired_at = datetime.utcnow()
    esc.total_alerts_sent = (esc.total_alerts_sent or 0) + 1
    db.add(esc)
    db.commit()
    db.close()


def schedule_retries(escalation_id: int, interval_minutes: int = 15):
    # Add a recurring job that runs every interval_minutes until acknowledged
    job_id = f"escalation_retry_{escalation_id}"

    def job():
        db = SessionLocal()
        esc = db.query(Escalation).filter(Escalation.escalation_id == escalation_id).first()
        if not esc:
            logger.info("No escalation; removing job %s", job_id)
            db.close()
            try:
                sched.remove_job(job_id)
            except Exception:
                pass
            return

        if esc.acknowledgement_received_at:
            logger.info("Escalation %s acknowledged; removing job", escalation_id)
            db.close()
            try:
                sched.remove_job(job_id)
            except Exception:
                pass
            return

        # Fire alerts
        fire_alerts(escalation_id)

        # If reached 3 alerts, next ones will also notify backup (handled in fire_alerts)
        db.close()

    sched.add_job(
        job,
        "interval",
        minutes=interval_minutes,
        id=job_id,
        next_run_time=datetime.utcnow() + timedelta(minutes=interval_minutes),
    )


def start():
    if not sched.running:
        sched.start()


def stop():
    if sched.running:
        sched.shutdown(wait=False)
