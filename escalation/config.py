import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./escalation.db")
    enable_external_notifications: bool = _as_bool(
        os.getenv("ENABLE_EXTERNAL_NOTIFICATIONS")
    )
    twilio_account_sid: str | None = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_sms_from_number: str | None = os.getenv("TWILIO_SMS_FROM_NUMBER")
    twilio_whatsapp_from_number: str | None = os.getenv(
        "TWILIO_WHATSAPP_FROM_NUMBER"
    )
    sendgrid_api_key: str | None = os.getenv("SENDGRID_API_KEY")
    sendgrid_from_email: str | None = os.getenv("SENDGRID_FROM_EMAIL")
    sendgrid_from_name: str = os.getenv(
        "SENDGRID_FROM_NAME", "Vakil Escalation"
    )
    dashboard_webhook_url: str | None = os.getenv("DASHBOARD_WEBHOOK_URL")
    dashboard_webhook_token: str | None = os.getenv("DASHBOARD_WEBHOOK_TOKEN")


settings = Settings()

