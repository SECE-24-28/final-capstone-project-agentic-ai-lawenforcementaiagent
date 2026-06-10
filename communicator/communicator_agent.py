import logging
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request

from database.db import init_db, get_client_by_id
from communicator.message_templates import render_template
from communicator.whatsapp_client import send_whatsapp
from communicator.reply_handler import handle_incoming_reply

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("communicator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
app = Flask(__name__)

# ── Action → Template mapping ────────────────────────────────
ACTION_TEMPLATE_MAP = {
    "NOTIFY_CLIENT_NEW_HEARING":   "NEW_HEARING_DATE",
    "NOTIFY_CLIENT_URGENT_HEARING": "URGENT_HEARING",
    "SEND_ORDER_SUMMARY":          "ORDER_SUMMARY",
    "SEND_URGENT_ALERT":           "URGENT_ALERT",
    "SEND_VICTORY_MESSAGE":        "CASE_VICTORY",
    "SEND_INTRODUCTION":           "INTRODUCTION",
}

# ── Requires lawyer approval before sending ──────────────────
REQUIRES_APPROVAL = {"SEND_ORDER_SUMMARY", "SEND_VICTORY_MESSAGE", "SEND_INTRODUCTION"}

# Approval queue: { instruction_id: instruction }
_approval_queue = {}


def receive_instruction(instruction: dict):
    """
    Entry point called by Reasoner Agent.
    instruction example:
    {
        action: "NOTIFY_CLIENT_URGENT_HEARING",
        case_id: "OS234/2024",
        client_id: "CLIENT_KUMAR_001",
        client_phone: "9876543210",
        client_language: "tamil",
        hearing_date: "10-06-2025",
        hearing_time: "10:00 AM",
        court_hall: "Hall 3",
        court_name: "Madurai District Court",
        documents_needed: ["original title deed", "aadhar card"],
        advocate_name: "Rajan",
        urgency: "HIGH",
        require_confirmation: True
    }
    """
    action = instruction.get("action")

    if action in REQUIRES_APPROVAL:
        _queue_for_approval(instruction)
        return

    _send_instruction(instruction)


def _send_instruction(instruction: dict):
    action   = instruction.get("action")
    template = ACTION_TEMPLATE_MAP.get(action)

    if not template:
        logger.error(f"Unknown action: {action}")
        return

    lang  = instruction.get("client_language", "tamil")
    phone = instruction.get("client_phone")

    # Build variables for template
    variables = {
        "client_name":   instruction.get("client_name", ""),
        "advocate_name": instruction.get("advocate_name", ""),
        "advocate_phone": instruction.get("advocate_phone", ""),
        "case_number":   instruction.get("case_id", ""),
        "hearing_date":  instruction.get("hearing_date", ""),
        "hearing_time":  instruction.get("hearing_time", ""),
        "court_name":    instruction.get("court_name", ""),
        "court_hall":    instruction.get("court_hall", ""),
        "documents":     instruction.get("documents_needed", []),
        "order_date":    instruction.get("order_date", ""),
        "order_summary": instruction.get("order_summary", ""),
        "next_action":   instruction.get("next_action", ""),
        "deadline":      instruction.get("deadline", ""),
    }

    message = render_template(template, lang, variables)

    meta = {
        "case_id":      instruction.get("case_id"),
        "client_id":    instruction.get("client_id"),
        "message_type": template,
        "language":     lang,
    }

    success = send_whatsapp(phone, message, meta)

    if success and instruction.get("require_confirmation"):
        _start_reply_tracker(instruction)

    # Schedule 24hr and 2hr reminders for hearings
    if action in ("NOTIFY_CLIENT_NEW_HEARING", "NOTIFY_CLIENT_URGENT_HEARING"):
        _schedule_reminders(instruction)


def _schedule_reminders(instruction: dict):
    hearing_date = instruction.get("hearing_date")
    hearing_time = instruction.get("hearing_time", "10:00 AM")

    try:
        hearing_dt = datetime.strptime(
            f"{hearing_date} {hearing_time}", "%d-%m-%Y %I:%M %p"
        )
        reminder_2hr = hearing_dt - timedelta(hours=2)

        if reminder_2hr > datetime.now():
            reminder_instruction = {**instruction, "action": "TWO_HOUR_REMINDER"}
            scheduler.add_job(
                _send_two_hour_reminder,
                'date',
                run_date=reminder_2hr,
                args=[instruction],
                id=f"2hr_{instruction.get('client_id')}_{hearing_date}"
            )
            logger.info(f"2hr reminder scheduled for {reminder_2hr}")
    except Exception as e:
        logger.warning(f"Could not schedule reminder: {e}")


def _send_two_hour_reminder(instruction: dict):
    lang  = instruction.get("client_language", "tamil")
    phone = instruction.get("client_phone")
    variables = {
        "client_name":   instruction.get("client_name", ""),
        "advocate_name": instruction.get("advocate_name", ""),
        "hearing_time":  instruction.get("hearing_time", ""),
        "court_name":    instruction.get("court_name", ""),
        "court_hall":    instruction.get("court_hall", ""),
    }
    message = render_template("TWO_HOUR_REMINDER", lang, variables)
    meta = {
        "case_id":      instruction.get("case_id"),
        "client_id":    instruction.get("client_id"),
        "message_type": "TWO_HOUR_REMINDER",
        "language":     lang,
    }
    send_whatsapp(phone, message, meta)
    logger.info(f"2hr reminder sent to {phone}")


def _start_reply_tracker(instruction: dict):
    """Check every 30 min if client replied. Send follow-up if not."""
    client_id = instruction.get("client_id")
    scheduler.add_job(
        _check_reply,
        'interval',
        minutes=30,
        id=f"reply_tracker_{client_id}",
        args=[instruction, 0],
        max_instances=1
    )
    logger.info(f"Reply tracker started for client {client_id}")


def _check_reply(instruction: dict, attempt: int):
    from database.db import get_last_message_context
    client_id = instruction.get("client_id")
    context   = get_last_message_context(client_id)

    if context.get("reply_classified_as"):
        # Reply received — stop tracker
        job_id = f"reply_tracker_{client_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        return

    if attempt >= 2:
        # No reply after 2 checks — alert escalation
        from communicator.reply_handler import escalation_agent_alert
        escalation_agent_alert({
            "type":      "NO_RESPONSE",
            "client_id": client_id,
        })
        if scheduler.get_job(f"reply_tracker_{client_id}"):
            scheduler.remove_job(f"reply_tracker_{client_id}")
        return

    # Send follow-up reminder
    lang  = instruction.get("client_language", "tamil")
    phone = instruction.get("client_phone")
    followup = render_template("ACK_UNCLEAR", lang, {})
    meta = {
        "client_id":    client_id,
        "message_type": "FOLLOWUP",
        "language":     lang,
    }
    send_whatsapp(phone, followup, meta)


def _queue_for_approval(instruction: dict):
    import uuid
    inst_id = str(uuid.uuid4())
    _approval_queue[inst_id] = instruction
    logger.info(f"Instruction queued for lawyer approval: {inst_id} | {instruction.get('action')}")
    # Lawyer approves via /approve/<inst_id> endpoint below


# ── Flask Webhook — Incoming WhatsApp replies ────────────────
@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    phone      = request.form.get("From", "").replace("whatsapp:+91", "")
    reply_text = request.form.get("Body", "").strip()
    if phone and reply_text:
        handle_incoming_reply(phone, reply_text)
    return "OK", 200


@app.route("/webhook/status", methods=["POST"])
def status_webhook():
    from communicator.whatsapp_client import update_status_from_webhook
    sid    = request.form.get("MessageSid")
    status = request.form.get("MessageStatus")
    if sid and status:
        update_status_from_webhook(sid, status)
    return "OK", 200


@app.route("/approve/<inst_id>", methods=["POST"])
def approve_instruction(inst_id):
    instruction = _approval_queue.pop(inst_id, None)
    if not instruction:
        return "Not found", 404
    _send_instruction(instruction)
    return "Sent", 200


if __name__ == "__main__":
    init_db()
    scheduler.start()
    logger.info("Communicator Agent started")
    app.run(port=5001, debug=False)
