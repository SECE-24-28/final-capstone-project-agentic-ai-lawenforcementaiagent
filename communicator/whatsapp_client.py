import os
import logging
from twilio.rest import Client
from dotenv import load_dotenv
from database.db import save_message, update_delivery_status

load_dotenv()
logger = logging.getLogger(__name__)

_twilio = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")


def send_whatsapp(phone: str, message: str, message_meta: dict) -> bool:
    """Send WhatsApp message. Falls back to SMS if WhatsApp fails."""
    try:
        msg = _twilio.messages.create(
            from_=WHATSAPP_FROM,
            to=f"whatsapp:+91{phone}",
            body=message
        )
        logger.info(f"WhatsApp sent to {phone} | sid={msg.sid}")
        save_message({**message_meta, "content_sent": message, "delivery_status": "sent"})
        return True

    except Exception as e:
        logger.warning(f"WhatsApp failed for {phone}: {e}. Trying SMS fallback.")
        return _send_sms(phone, message, message_meta)


def _send_sms(phone: str, message: str, message_meta: dict) -> bool:
    try:
        msg = _twilio.messages.create(
            from_=os.getenv("TWILIO_SMS_FROM", WHATSAPP_FROM),
            to=f"+91{phone}",
            body=message
        )
        logger.info(f"SMS sent to {phone} | sid={msg.sid}")
        save_message({**message_meta, "content_sent": message, "delivery_status": "sent"})
        return True

    except Exception as e:
        logger.error(f"SMS also failed for {phone}: {e}")
        save_message({**message_meta, "content_sent": message, "delivery_status": "failed"})
        return False


def update_status_from_webhook(message_sid: str, status: str):
    """Called by Flask webhook when Twilio sends delivery updates."""
    update_delivery_status(message_sid, status)
    logger.info(f"Delivery status updated: {message_sid} → {status}")
