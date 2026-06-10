from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

# Fields to monitor and their event types
FIELD_EVENT_MAP = {
    "next_hearing_date": "DATE_CHANGED",
    "last_order_date":   "NEW_ORDER",
    "last_order_pdf":    "NEW_ORDER",
    "status":            "STATUS_CHANGED",
    "judge":             "JUDGE_CHANGED",
    "court_hall":        "HALL_CHANGED",
    "opponent_filing":   "NEW_FILING",
}


def _is_tomorrow(date_str):
    if not date_str:
        return False
    try:
        hearing = datetime.strptime(date_str, "%d-%m-%Y").date()
        return hearing == date.today() + timedelta(days=1)
    except ValueError:
        return False


def _is_within_24hrs(date_str):
    if not date_str:
        return False
    try:
        hearing = datetime.strptime(date_str, "%d-%m-%Y").date()
        return hearing <= date.today() + timedelta(days=1)
    except ValueError:
        return False


def detect_changes(stored: dict, api: dict):
    """
    Compare stored DB state with fresh API response.
    Returns list of event dicts for every change found.
    """
    events = []

    # 1. Hearing date — new or changed
    old_date = stored.get("last_known_next_date")
    new_date = api.get("next_hearing_date")
    if old_date != new_date:
        if old_date is None and new_date:
            event_type = "NEW_DATE"
        elif new_date is None:
            event_type = "DATE_CANCELLED"
        else:
            event_type = "DATE_CHANGED"
        events.append({
            "event_type":          event_type,
            "old_value":           str(old_date) if old_date else None,
            "new_value":           new_date,
            "less_than_24_hours":  _is_within_24hrs(new_date),
        })

    # 2. New order PDF
    old_pdf = stored.get("last_known_order_pdf")
    new_pdf = api.get("last_order_pdf")
    if new_pdf and old_pdf != new_pdf:
        events.append({
            "event_type": "NEW_ORDER",
            "old_value":  old_pdf,
            "new_value":  new_pdf,
            "pdf_url":    api.get("order_pdf_url"),
            "less_than_24_hours": False,
        })

    # 3. Opponent new filing
    old_filing = stored.get("last_known_filing")
    new_filing = api.get("opponent_filing")
    if new_filing and old_filing != new_filing:
        events.append({
            "event_type": "NEW_FILING",
            "old_value":  old_filing,
            "new_value":  new_filing,
            "pdf_url":    api.get("filing_pdf_url"),
            "less_than_24_hours": False,
        })

    # 4. Case status
    old_status = stored.get("last_known_status")
    new_status = api.get("status")
    if new_status and old_status != new_status:
        event_type = "CASE_DISPOSED" if new_status == "disposed" else "STATUS_CHANGED"
        events.append({
            "event_type": event_type,
            "old_value":  old_status,
            "new_value":  new_status,
            "less_than_24_hours": False,
        })

    # 5. Judge change
    old_judge = stored.get("last_known_judge")
    new_judge = api.get("judge")
    if new_judge and old_judge != new_judge:
        events.append({
            "event_type": "JUDGE_CHANGED",
            "old_value":  old_judge,
            "new_value":  new_judge,
            "less_than_24_hours": False,
        })

    # 6. Court hall change
    old_hall = stored.get("last_known_hall")
    new_hall = api.get("court_hall")
    if new_hall and old_hall != new_hall:
        events.append({
            "event_type": "HALL_CHANGED",
            "old_value":  old_hall,
            "new_value":  new_hall,
            "less_than_24_hours": False,
        })

    # 7. Cause list / urgent listing
    if api.get("cause_list_today"):
        events.append({
            "event_type": "CAUSE_LIST_ADDED",
            "old_value":  None,
            "new_value":  "listed_today",
            "less_than_24_hours": True,
        })

    if api.get("no_adjournment_note"):
        events.append({
            "event_type": "URGENT_LISTING",
            "old_value":  None,
            "new_value":  "no_adjournment",
            "less_than_24_hours": True,
        })

    return events


def build_event(case: dict, change: dict):
    """Build full event object to pass to Reasoner Agent."""
    return {
        "case_id":             case["case_id"],
        "case_number":         case["case_number"],
        "event_type":          change["event_type"],
        "old_value":           change.get("old_value"),
        "new_value":           change.get("new_value"),
        "pdf_url":             change.get("pdf_url"),
        "less_than_24_hours":  change.get("less_than_24_hours", False),
        "detected_at":         datetime.now().isoformat(),
        "advocate_id":         case.get("advocate_id"),
        "client_id":           case.get("client_id"),
    }
