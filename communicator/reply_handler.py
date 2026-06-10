import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from database.db import get_client_by_phone, get_last_message_context, save_reply, opt_out_client
from communicator.message_templates import render_template
from communicator.whatsapp_client import send_whatsapp

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_model = genai.GenerativeModel("gemini-1.5-flash")

OPT_OUT_KEYWORDS = ["stop", "இனி செய்தி அனுப்பாதீர்கள்", "message mat bhejo", "unsubscribe"]


# ── Stubs for other agents ───────────────────────────────────
def escalation_agent_alert(data):
    logger.warning(f"→ Escalation: {data}")

def lawyer_alert(advocate_id, message):
    logger.warning(f"→ Lawyer {advocate_id}: {message}")


def _classify_reply(reply_text: str, context: dict) -> str:
    prompt = (
        f"Context: {context.get('message_type', 'hearing reminder')}.\n"
        f"We asked the client about their court case.\n"
        f"Client replied: \"{reply_text}\"\n"
        f"Classify as exactly one of: "
        f"CONFIRMED / CANNOT_ATTEND / PROBLEM_DETECTED / NEEDS_INFO / OPT_OUT / UNCLEAR"
    )
    try:
        res = _model.generate_content(prompt)
        classification = res.text.strip().upper()
        for valid in ("CONFIRMED", "CANNOT_ATTEND", "PROBLEM_DETECTED", "NEEDS_INFO", "OPT_OUT", "UNCLEAR"):
            if valid in classification:
                return valid
        return "UNCLEAR"
    except Exception as e:
        logger.error(f"Claude classification failed: {e}")
        return "UNCLEAR"


def _meta(client):
    return {
        "client_id": client["client_id"],
        "message_type": "REPLY",
        "language": client["language_preference"],
    }


def handle_incoming_reply(phone: str, reply_text: str):
    # Check opt-out keywords first (no Claude needed)
    if any(kw in reply_text.lower() for kw in OPT_OUT_KEYWORDS):
        _handle_opt_out(phone, reply_text)
        return

    client = get_client_by_phone(phone)
    if not client:
        logger.warning(f"Unknown phone: {phone}")
        return

    lang     = client["language_preference"]
    context  = get_last_message_context(client["client_id"])
    classification = _classify_reply(reply_text, context)

    save_reply(client["client_id"], reply_text, classification)
    logger.info(f"Reply from {phone} classified as: {classification}")

    if classification == "CONFIRMED":
        _handle_confirmed(client, lang)

    elif classification == "CANNOT_ATTEND":
        _handle_cannot_attend(client, lang, reply_text)

    elif classification == "PROBLEM_DETECTED":
        _handle_problem(client, lang, reply_text)

    elif classification == "NEEDS_INFO":
        _handle_needs_info(client, lang, context)

    elif classification == "OPT_OUT":
        _handle_opt_out(phone, reply_text)

    else:
        _handle_unclear(client, lang, reply_text)


def _handle_confirmed(client, lang):
    ack = render_template("ACK_CONFIRMED", lang, {})
    send_whatsapp(client["phone_number"], ack, _meta(client))
    logger.info(f"Client {client['client_id']} confirmed attendance")
    # Reasoner will schedule 2hr reminder — stub call here
    # reasoner_agent.schedule_reminder(client["client_id"])


def _handle_cannot_attend(client, lang, reply_text):
    ack = render_template("ACK_CANNOT_ATTEND", lang, {})
    send_whatsapp(client["phone_number"], ack, _meta(client))
    escalation_agent_alert({
        "type":      "CLIENT_CANNOT_ATTEND",
        "client_id": client["client_id"],
        "reason":    reply_text,
    })
    logger.warning(f"Client {client['client_id']} cannot attend")


def _handle_problem(client, lang, reply_text):
    ack = render_template("ACK_PROBLEM", lang,
                          {"advocate_name": "உங்கள் வக்கீல்"})
    send_whatsapp(client["phone_number"], ack, _meta(client))
    escalation_agent_alert({
        "type":      "CLIENT_PROBLEM",
        "client_id": client["client_id"],
        "problem":   reply_text,
    })
    logger.warning(f"Client {client['client_id']} has a problem: {reply_text}")


def _handle_needs_info(client, lang, context):
    info = context.get("content_sent", "Please contact your advocate directly.")
    send_whatsapp(client["phone_number"], info, _meta(client))


def _handle_unclear(client, lang, reply_text):
    ack = render_template("ACK_UNCLEAR", lang, {})
    send_whatsapp(client["phone_number"], ack, _meta(client))

    # After 2 unclear replies, forward raw message to lawyer
    save_reply(client["client_id"], reply_text, "UNCLEAR")
    lawyer_alert(
        client["advocate_id"],
        f"Client {client['name']} sent unclear message: \"{reply_text}\". Please review."
    )


def _handle_opt_out(phone: str, reply_text: str):
    client = get_client_by_phone(phone)
    if not client:
        return
    opt_out_client(client["client_id"])
    lang = client["language_preference"]
    ack  = render_template("OPT_OUT_CONFIRM", lang, {})
    send_whatsapp(phone, ack, _meta(client))
    lawyer_alert(
        client["advocate_id"],
        f"Client {client['name']} has opted out of WhatsApp messages. Please communicate directly."
    )
    logger.info(f"Client {client['client_id']} opted out")
