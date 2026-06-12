# e:\VakilAI\drafter_agent\reasoner_agent\database.py
import psycopg2
import psycopg2.extras
import json
import time
from datetime import datetime
from typing import Dict, Any
from config import DATABASE_URL, logger

_MAX_RETRIES = 3
_RETRY_WAIT = 2  # seconds

def _get_connection():
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            logger.error(
                f"DB connection attempt {attempt} failed: {e}"
            )
            if attempt == _MAX_RETRIES:
                raise
            time.sleep(_RETRY_WAIT)

# ----------------------------------------------------------------------
# 1️⃣ Pull full case history
# ----------------------------------------------------------------------
def get_case_full_history(case_id: str) -> Dict[str, Any]:
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # cases
            cur.execute(
                """
                SELECT id, case_number, court_name, court_type, case_type,
                       risk_score, adjournment_count, last_order_text,
                       last_order_date, status, created_at, advocate_id,
                       client_id
                FROM cases
                WHERE id = %s
                """,
                (case_id,),
            )
            case = cur.fetchone()
            if not case:
                raise ValueError(f"Case {case_id} not found")

            # case_history (last 5 orders + all hearing dates)
            cur.execute(
                """
                SELECT hearing_date, order_text, filing_by, notes, created_at
                FROM case_history
                WHERE case_id = %s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (case_id,),
            )
            history = cur.fetchall()

            # lawyer_tags
            cur.execute(
                """
                SELECT tag, added_by, created_at
                FROM lawyer_tags
                WHERE case_id = %s
                """,
                (case_id,),
            )
            tags = cur.fetchall()

            return {
                "case": dict(case),
                "history": [dict(r) for r in history],
                "tags": [dict(t) for t in tags],
            }
    finally:
        conn.close()

# ----------------------------------------------------------------------
# 2️⃣ Update risk score (capped at 100)
# ----------------------------------------------------------------------
def update_risk_score(case_id: str, new_score: int):
    new_score = min(new_score, 100)
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE cases
                SET risk_score = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (new_score, case_id),
            )
            conn.commit()
    finally:
        conn.close()

# ----------------------------------------------------------------------
# 3️⃣ Save processed event to case_events
# ----------------------------------------------------------------------
def save_event_to_db(
    case_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    detected_at: datetime,
    urgency: str,
    action_pkg: Dict[str, Any],
):
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO case_events
                (case_id, event_type, event_data, detected_at,
                 urgency, action_package, processed, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW())
                """,
                (
                    case_id,
                    event_type,
                    json.dumps(event_data),
                    detected_at,
                    urgency,
                    json.dumps(action_pkg),
                ),
            )
            conn.commit()
    finally:
        conn.close()

# ----------------------------------------------------------------------
# 4️⃣ Add a lawyer tag (used for overrides & safety checks)
# ----------------------------------------------------------------------
def add_lawyer_tag(case_id: str, tag: str, added_by: str):
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lawyer_tags (case_id, tag, added_by, created_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (case_id, tag, added_by),
            )
            conn.commit()
    finally:
        conn.close()
