# e:\VakilAI\drafter_agent\reasoner_agent\safety_checks.py
from typing import List, Dict, Any, Tuple
from config import URGENCY, logger
from datetime import datetime, timezone

# ----------------------------------------------------------------------
# Helper to upgrade urgency (never downgrade)
# ----------------------------------------------------------------------
def _upgrade(current: str, target: str) -> str:
    order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if order.index(target) > order.index(current):
        return target
    return current

# ----------------------------------------------------------------------
# 1️⃣ Lawyer context tags
# ----------------------------------------------------------------------
def safety_check_1(tags: List[Dict[str, Any]], urgency: str) -> str:
    critical_tags = {
        "last adjournment possible",
        "judge gave verbal warning",
        "critical compliance pending",
        "final opportunity",
        "judge is impatient",
    }
    tag_set = {t["tag"].lower() for t in tags}
    if tag_set.intersection(critical_tags):
        new = _upgrade(urgency, URGENCY["HIGH"])
        logger.info(f"Safety check 1 upgraded urgency to {new}")
        return new
    return urgency

# ----------------------------------------------------------------------
# 2️⃣ Adjournment counter
# ----------------------------------------------------------------------
def safety_check_2(adj_count: int, urgency: str) -> str:
    if adj_count >= 4:
        new = _upgrade(urgency, URGENCY["HIGH"])
    elif adj_count == 3 and urgency == URGENCY["LOW"]:
        new = _upgrade(urgency, URGENCY["MEDIUM"])
    else:
        new = urgency
    if new != urgency:
        logger.info(f"Safety check 2 upgraded urgency to {new}")
    return new

# ----------------------------------------------------------------------
# 3️⃣ Risk score
# ----------------------------------------------------------------------
def safety_check_3(risk_score: int, urgency: str) -> str:
    if risk_score >= 60:
        new = _upgrade(urgency, URGENCY["CRITICAL"])
    elif 41 <= risk_score <= 59 and urgency == URGENCY["LOW"]:
        new = _upgrade(urgency, URGENCY["HIGH"])
    elif 21 <= risk_score <= 40 and urgency == URGENCY["LOW"]:
        new = _upgrade(urgency, URGENCY["MEDIUM"])
    else:
        new = urgency
    if new != urgency:
        logger.info(f"Safety check 3 upgraded urgency to {new}")
    return new

# ----------------------------------------------------------------------
# 4️⃣ Time until next hearing
# ----------------------------------------------------------------------
def safety_check_4(event_data: Dict[str, Any], urgency: str) -> str:
    # Expect event_data may contain 'hearing_datetime' ISO string
    dt_str = event_data.get("hearing_datetime")
    if not dt_str:
        return urgency
    try:
        hearing_dt = datetime.fromisoformat(dt_str)
        now = datetime.now(timezone.utc)
        diff_hours = (hearing_dt - now).total_seconds() / 3600
        if diff_hours < 3:
            new = _upgrade(urgency, URGENCY["CRITICAL"])
        elif diff_hours < 24 and urgency in (URGENCY["LOW"], URGENCY["MEDIUM"]):
            new = _upgrade(urgency, URGENCY["HIGH"])
        else:
            new = urgency
        if new != urgency:
            logger.info(f"Safety check 4 upgraded urgency to {new}")
        return new
    except Exception:
        return urgency

# ----------------------------------------------------------------------
# 5️⃣ Suspicious pattern detection
# ----------------------------------------------------------------------
def safety_check_5(
    adj_count: int,
    days_since_last_petitioner: int,
    last_order_text: str,
    urgency: str,
) -> str:
    pattern = (
        adj_count >= 3
        and days_since_last_petitioner > 60
        and any(word in last_order_text.lower() for word in ("compliance", "produce", "directed to"))
    )
    if pattern:
        new = _upgrade(urgency, URGENCY["HIGH"])
        logger.info(f"Safety check 5 upgraded urgency to {new}")
        return new
    return urgency

# ----------------------------------------------------------------------
# Orchestrator – run all checks in order
# ----------------------------------------------------------------------
def run_all_safety_checks(
    case_data: Dict[str, Any],
    initial_urgency: str,
    event_data: Dict[str, Any],
) -> str:
    urgency = initial_urgency
    urgency = safety_check_1(case_data["tags"], urgency)
    urgency = safety_check_2(case_data["case"]["adjournment_count"], urgency)
    urgency = safety_check_3(case_data["case"]["risk_score"], urgency)
    urgency = safety_check_4(event_data, urgency)
    # calculate days since last petitioner activity
    last_petitioner = max(
        (
            h["created_at"]
            for h in case_data["history"]
            if h.get("filing_by") == "petitioner"
        ),
        default=None,
    )
    if last_petitioner:
        days_since = (datetime.now(timezone.utc) - last_petitioner).days
    else:
        days_since = 9999
    urgency = safety_check_5(
        case_data["case"]["adjournment_count"],
        days_since,
        case_data["case"]["last_order_text"] or "",
        urgency,
    )
    return urgency

# ----------------------------------------------------------------------
# Risk‑score calculator (rule‑based)
# ----------------------------------------------------------------------
def calculate_risk_score(case_data: Dict[str, Any]) -> Tuple[int, List[str]]:
    points = 0
    reasons = []

    adj = case_data["case"]["adjournment_count"]
    points += 10 * adj
    if adj:
        reasons.append(f"{adj} adjournments (+{10*adj})")

    # opponent filing in last 7 days
    now = datetime.now(timezone.utc)
    recent_opponent = any(
        (now - h["created_at"]).days <= 7 and h["filing_by"] == "respondent"
        for h in case_data["history"]
    )
    if recent_opponent:
        points += 15
        reasons.append("Opponent filed in last 7 days (+15)")

    # lawyer tag "judge verbal warning"
    if any(t["tag"].lower() == "judge gave verbal warning" for t in case_data["tags"]):
        points += 30
        reasons.append("Judge verbal warning tag (+30)")

    # last order compliance words
    last_order = (case_data["case"]["last_order_text"] or "").lower()
    if any(word in last_order for word in ("compliance", "produce", "directed to")):
        points += 20
        reasons.append("Compliance wording in last order (+20)")

    # no petitioner activity last 30 days
    last_petitioner = max(
        (
            h["created_at"]
            for h in case_data["history"]
            if h.get("filing_by") == "petitioner"
        ),
        default=None,
    )
    if not last_petitioner or (now - last_petitioner).days > 30:
        points += 10
        reasons.append("No petitioner activity >30 days (+10)")

    # last order contains "final opportunity" or "last chance"
    if any(phrase in last_order for phrase in ("final opportunity", "last chance")):
        points += 15
        reasons.append('Last order contains "final opportunity"/"last chance" (+15)')

    # case age in years
    created_at = case_data["case"]["created_at"]
    age_years = (now - created_at).days // 365
    points += 5 * age_years
    reasons.append(f"Case age {age_years} years (+{5*age_years})")

    # criminal case
    if case_data["case"]["case_type"] == "criminal":
        points += 25
        reasons.append("Criminal case (+25)")

    # any order or filing contains "contempt"
    if any("contempt" in (h.get("order_text") or "").lower() for h in case_data["history"]):
        points += 35
        reasons.append('Order/filing contains "contempt" (+35)')

    points = min(points, 100)
    return points, reasons
