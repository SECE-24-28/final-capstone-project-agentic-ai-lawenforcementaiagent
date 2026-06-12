import psycopg2
from config import DATABASE_URL, logger

CREATE_TABLES_SQL = """
-- Drop old tables if running fresh, otherwise remove CASCADE directives in production
DROP TABLE IF EXISTS cases CASCADE;
DROP TABLE IF EXISTS case_history CASCADE;
DROP TABLE IF EXISTS lawyer_tags CASCADE;
DROP TABLE IF EXISTS case_events CASCADE;

CREATE TABLE cases (
    id VARCHAR(50) PRIMARY KEY,
    case_number VARCHAR(100),
    court_name VARCHAR(255),
    court_type VARCHAR(100),
    case_type VARCHAR(100),
    advocate_id VARCHAR(50),
    client_id VARCHAR(50),
    risk_score INTEGER DEFAULT 0,
    adjournment_count INTEGER DEFAULT 0,
    last_order_text TEXT,
    last_order_date DATE,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE case_history (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(id) ON DELETE CASCADE,
    hearing_date DATE,
    order_text TEXT,
    filing_by VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE lawyer_tags (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(id) ON DELETE CASCADE,
    tag VARCHAR(255),
    added_by VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE case_events (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(id) ON DELETE CASCADE,
    event_type VARCHAR(100),
    event_data JSONB,
    detected_at TIMESTAMP WITH TIME ZONE,
    urgency VARCHAR(50),
    action_package JSONB,
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Recreate Drafter documents table so Drafter Agent continues to work
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(id) ON DELETE CASCADE, 
    document_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    client_content TEXT,
    language VARCHAR(50),
    edited_content TEXT,
    approval_status VARCHAR(50) DEFAULT 'pending',
    lawyer_approval_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add some dummy data just to test analysis pipeline
INSERT INTO cases (id, case_number, court_name, court_type, case_type, advocate_id, client_id, risk_score, adjournment_count, status)
VALUES ('CASE123', 'CS-2023-01', 'Madras High Court', 'High Court', 'civil', 'ADV-001', 'CLI-001', 10, 1, 'active')
ON CONFLICT (id) DO NOTHING;
"""

def init_db():
    try:
        logger.info(f"Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLES_SQL)
            conn.commit()
        logger.info("Successfully initialized all database schemas for Reasoner Agent.")
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_db()
