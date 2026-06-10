import logging
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime

from database.db import (
    init_db, fetch_active_cases, save_event,
    update_case_state, update_last_checked, log_api_failure, resolve_api_failure
)
from watcher.api_client import fetch_case, APIDownException
from watcher.change_detector import detect_changes, build_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("watcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ── Stubs for other agents (teammates will fill these) ───────
def reasoner_agent_process(event):
    logger.info(f"→ Reasoner: {event['event_type']} for {event['case_number']}")

def supervisor_agent_alert(message):
    logger.critical(f"→ Supervisor: {message}")


# ── Field map: event type → which DB column to update ────────
STATE_UPDATE_MAP = {
    "NEW_DATE":       "last_known_next_date",
    "DATE_CHANGED":   "last_known_next_date",
    "DATE_CANCELLED": "last_known_next_date",
    "NEW_ORDER":      ("last_known_order_date", "last_known_order_pdf"),
    "STATUS_CHANGED": "last_known_status",
    "CASE_DISPOSED":  "last_known_status",
    "JUDGE_CHANGED":  "last_known_judge",
    "HALL_CHANGED":   "last_known_hall",
}


def _update_case_state_from_event(case, event, api_data):
    """Update only the changed fields in DB after a change is detected."""
    updates = {}

    if event["event_type"] in ("NEW_DATE", "DATE_CHANGED", "DATE_CANCELLED"):
        updates["last_known_next_date"] = event["new_value"]

    elif event["event_type"] == "NEW_ORDER":
        updates["last_known_order_date"] = api_data.get("last_order_date")
        updates["last_known_order_pdf"]  = event["new_value"]

    elif event["event_type"] in ("STATUS_CHANGED", "CASE_DISPOSED"):
        updates["last_known_status"] = event["new_value"]
        if event["event_type"] == "CASE_DISPOSED":
            updates["status"] = "disposed"

    elif event["event_type"] == "JUDGE_CHANGED":
        updates["last_known_judge"] = event["new_value"]

    elif event["event_type"] == "HALL_CHANGED":
        updates["last_known_hall"] = event["new_value"]

    if updates:
        update_case_state(case["case_id"], updates)


def check_all_cases():
    logger.info("━━━ Watcher poll started ━━━")
    cases = fetch_active_cases()

    if not cases:
        logger.info("No active cases to check.")
        return

    api_down_cases = []

    for case in cases:
        case_number = case["case_number"]
        try:
            api_data, api_used = fetch_case(case_number, case.get("case_type", "district"))

            # Resolve any previous failure log
            resolve_api_failure(api_used)

            # Detect all changes
            changes = detect_changes(case, api_data)

            if changes:
                for change in changes:
                    event = build_event(case, change)

                    # Save to DB
                    save_event(event)

                    # Update stored state
                    _update_case_state_from_event(case, event, api_data)

                    # Pass to Reasoner Agent
                    reasoner_agent_process(event)

                    logger.info(
                        f"{case_number} → {event['event_type']} detected "
                        f"| 24hr={event['less_than_24_hours']}"
                    )
            else:
                logger.info(f"{case_number} → No changes")

            update_last_checked(case["case_id"])

        except APIDownException as e:
            logger.error(f"API down for {case_number}: {e}")
            log_api_failure(case_number, "all", str(e))
            api_down_cases.append(case_number)

    if api_down_cases:
        supervisor_agent_alert(
            f"eCourts API unreachable. "
            f"{len(api_down_cases)} cases not checked since {datetime.now().strftime('%H:%M')}. "
            f"Cases: {', '.join(api_down_cases)}"
        )

    logger.info("━━━ Watcher poll complete ━━━\n")


if __name__ == "__main__":
    init_db()
    logger.info("Watcher Agent started — polling every 15 minutes")

    # Run once immediately on start
    check_all_cases()

    scheduler = BlockingScheduler()
    scheduler.add_job(check_all_cases, 'interval', minutes=15)
    scheduler.start()
