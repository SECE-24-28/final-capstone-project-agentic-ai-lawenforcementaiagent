import logging
from datetime import datetime
import json
from urllib.request import Request, urlopen

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Email, Mail
from twilio.rest import Client

from .config import settings

logger = logging.getLogger("escalation.notifiers")


def _simulated(channel: str):
    return {
        "status": "simulated",
        "channel": channel,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _require(channel: str, **values):
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            f"{channel} is enabled but missing configuration: {', '.join(missing)}"
        )


def send_push(push_token: str, title: str, body: str, high_priority: bool = False):
    logger.info(f"[Push] to={push_token} title={title} high={high_priority}")
    return _simulated("push")


def send_whatsapp(number: str, text: str):
    logger.info(f"[WhatsApp] to={number} text={text[:80]}")
    if not settings.enable_external_notifications:
        return _simulated("whatsapp")

    _require(
        "Twilio WhatsApp",
        TWILIO_ACCOUNT_SID=settings.twilio_account_sid,
        TWILIO_AUTH_TOKEN=settings.twilio_auth_token,
        TWILIO_WHATSAPP_FROM_NUMBER=settings.twilio_whatsapp_from_number,
    )
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    message = client.messages.create(
        from_=_whatsapp_address(settings.twilio_whatsapp_from_number),
        to=_whatsapp_address(number),
        body=text,
    )
    return {"status": "sent", "channel": "whatsapp", "message_id": message.sid}


def send_sms(number: str, text: str):
    logger.info(f"[SMS] to={number} text={text[:140]}")
    if not settings.enable_external_notifications:
        return _simulated("sms")

    _require(
        "Twilio SMS",
        TWILIO_ACCOUNT_SID=settings.twilio_account_sid,
        TWILIO_AUTH_TOKEN=settings.twilio_auth_token,
        TWILIO_SMS_FROM_NUMBER=settings.twilio_sms_from_number,
    )
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    message = client.messages.create(
        from_=settings.twilio_sms_from_number,
        to=number,
        body=text,
    )
    return {"status": "sent", "channel": "sms", "message_id": message.sid}


def send_email(email: str, subject: str, body: str, high_priority: bool = False):
    logger.info(f"[Email] to={email} subject={subject} high={high_priority}")
    if not settings.enable_external_notifications:
        return _simulated("email")

    _require(
        "SendGrid",
        SENDGRID_API_KEY=settings.sendgrid_api_key,
        SENDGRID_FROM_EMAIL=settings.sendgrid_from_email,
    )
    message = Mail(
        from_email=Email(
            settings.sendgrid_from_email,
            settings.sendgrid_from_name,
        ),
        to_emails=email,
        subject=subject,
        plain_text_content=body,
    )
    response = SendGridAPIClient(settings.sendgrid_api_key).send(message)
    return {
        "status": "sent",
        "channel": "email",
        "status_code": response.status_code,
    }


def update_dashboard(case_id: str, severity: str, brief: str):
    logger.info(f"[Dashboard] case={case_id} severity={severity}")
    if not settings.enable_external_notifications or not settings.dashboard_webhook_url:
        return _simulated("dashboard")

    headers = {"Content-Type": "application/json"}
    if settings.dashboard_webhook_token:
        headers["Authorization"] = f"Bearer {settings.dashboard_webhook_token}"
    request = Request(
        settings.dashboard_webhook_url,
        data=json.dumps(
            {"case_id": case_id, "severity": severity, "brief": brief}
        ).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return {
            "status": "sent",
            "channel": "dashboard",
            "status_code": response.status,
        }


def _whatsapp_address(number: str) -> str:
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"
