import psycopg2
from psycopg2 import pool
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ── Connection Pool ──────────────────────────────────────────
_pool = None

def init_db():
    global _pool
    _pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host="localhost",
        port=5432,
        database="vakil_ai",
        user="postgres",
        password="1234"
    )
    logger.info("Database pool initialized")

def get_conn():
    return _pool.getconn()

def release_conn(conn):
    _pool.putconn(conn)

# ── Generic Query Helper ─────────────────────────────────────
def execute(query, params=None, fetch=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB error: {e}")
        raise
    finally:
        release_conn(conn)

# ── Watcher Agent Functions ──────────────────────────────────

def fetch_active_cases():
    rows = execute("SELECT * FROM cases WHERE status = 'active'", fetch="all")
    if not rows:
        return []
    cols = ["case_id","case_number","court_name","case_type","advocate_id",
            "client_id","status","last_known_next_date","last_known_order_date",
            "last_known_order_pdf","last_known_status","last_known_judge",
            "last_known_hall","last_checked_at","created_at"]
    return [dict(zip(cols, row)) for row in rows]

def update_case_state(case_id, updates: dict):
    sets = ", ".join(f"{k} = %s" for k in updates)
    vals = list(updates.values()) + [case_id]
    execute(f"UPDATE cases SET {sets} WHERE case_id = %s", vals)

def update_last_checked(case_id):
    execute("UPDATE cases SET last_checked_at = %s WHERE case_id = %s",
            (datetime.now(), case_id))

def save_event(event: dict):
    execute("""
        INSERT INTO events
            (case_id, case_number, event_type, event_detected_at,
             old_value, new_value, pdf_url, less_than_24_hours)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        event.get("case_id"),
        event["case_number"],
        event["event_type"],
        event.get("detected_at", datetime.now()),
        event.get("old_value"),
        event.get("new_value"),
        event.get("pdf_url"),
        event.get("less_than_24_hours", False)
    ))

def mark_event_passed_to_reasoner(case_number):
    execute("""
        UPDATE events SET passed_to_reasoner_at = %s
        WHERE case_number = %s AND passed_to_reasoner_at IS NULL
    """, (datetime.now(), case_number))

def log_api_failure(case_number, api_used, reason):
    execute("""
        INSERT INTO api_failure_logs (case_number, api_used, failure_reason)
        VALUES (%s, %s, %s)
    """, (case_number, api_used, reason))

def resolve_api_failure(api_used):
    execute("""
        UPDATE api_failure_logs SET resolved_at = %s
        WHERE api_used = %s AND resolved_at IS NULL
    """, (datetime.now(), api_used))

# ── Communicator Agent Functions ─────────────────────────────

def get_client_by_phone(phone_number):
    row = execute(
        "SELECT * FROM clients WHERE phone_number = %s AND opted_out = FALSE",
        (phone_number,), fetch="one"
    )
    if not row:
        return None
    cols = ["client_id","advocate_id","name","phone_number","whatsapp_active",
            "language_preference","opted_out","opted_out_at",
            "first_message_sent","first_message_confirmed","created_at"]
    return dict(zip(cols, row))

def get_client_by_id(client_id):
    row = execute("SELECT * FROM clients WHERE client_id = %s",
                  (client_id,), fetch="one")
    if not row:
        return None
    cols = ["client_id","advocate_id","name","phone_number","whatsapp_active",
            "language_preference","opted_out","opted_out_at",
            "first_message_sent","first_message_confirmed","created_at"]
    return dict(zip(cols, row))

def save_message(msg: dict):
    execute("""
        INSERT INTO messages
            (case_id, client_id, message_type, language,
             content_sent, delivery_status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        msg.get("case_id"),
        msg["client_id"],
        msg["message_type"],
        msg["language"],
        msg["content_sent"],
        msg.get("delivery_status", "sent")
    ))

def save_reply(client_id, reply_text, classification):
    execute("""
        UPDATE messages
        SET reply_received = TRUE,
            reply_text = %s,
            reply_classified_as = %s,
            reply_received_at = %s
        WHERE client_id = %s
          AND reply_received = FALSE
        ORDER BY sent_at DESC
        LIMIT 1
    """, (reply_text, classification, datetime.now(), client_id))

def get_last_message_context(client_id):
    row = execute("""
        SELECT message_type, content_sent, sent_at
        FROM messages
        WHERE client_id = %s
        ORDER BY sent_at DESC LIMIT 1
    """, (client_id,), fetch="one")
    if not row:
        return {}
    return {"message_type": row[0], "content_sent": row[1], "sent_at": str(row[2])}

def opt_out_client(client_id):
    execute("""
        UPDATE clients
        SET opted_out = TRUE, opted_out_at = %s
        WHERE client_id = %s
    """, (datetime.now(), client_id))

def update_delivery_status(message_id, status):
    execute("UPDATE messages SET delivery_status = %s WHERE message_id = %s",
            (status, message_id))
