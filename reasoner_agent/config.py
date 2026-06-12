# e:\VakilAI\drafter_agent\reasoner_agent\config.py
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
import json

# Load .env from current directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# ----------------------------------------------------------------------
# Environment variables (with defaults where appropriate)
# ----------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8002"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
QUIET_HOURS_START = int(os.getenv("QUIET_HOURS_START", "23"))
QUIET_HOURS_END = int(os.getenv("QUIET_HOURS_END", "6"))

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
URGENCY = {
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH": "HIGH",
    "CRITICAL": "CRITICAL",
}

EVENT_TYPES = {
    "NEW_HEARING_DATE",
    "ORDER_PASSED",
    "OPPONENT_FILED",
    "CASE_DISMISSED",
    "CONTEMPT_FILED",
    "WARRANT_ISSUED",
    "STAY_APPLICATION",
    "SHOW_CAUSE_NOTICE",
    "FINAL_HEARING",
    "ADJOURNMENT_GRANTED",
    "EX_PARTE_ORDER",
    "APPEAL_FILED",
}

DIRECT_ESCALATION = {
    "CONTEMPT_FILED",
    "WARRANT_ISSUED",
    "CASE_DISMISSED",
    "EX_PARTE_ORDER",
    "STAY_APPLICATION",
    "SHOW_CAUSE_NOTICE",
}

REDIS_CHANNELS = {
    "REASONER": "reasoner_tasks",
    "ESCALATION": "escalation_tasks",
    "DRAFTER": "drafter_tasks",
    "COMMUNICATOR": "communicator_tasks",
    "SUPERVISOR": "supervisor_logs",
}

# ----------------------------------------------------------------------
# Logging – JSON format
# ----------------------------------------------------------------------
class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "source": "reasoner",
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

logger = logging.getLogger("reasoner")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
handler = logging.StreamHandler()
handler.setFormatter(JsonLogFormatter())
logger.addHandler(handler)
