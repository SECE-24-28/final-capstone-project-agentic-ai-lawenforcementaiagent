-- ============================================================
-- VakilAgent Database Schema
-- Teammate 2: Watcher Agent + Communicator Agent
-- ============================================================

-- Advocates (lawyers using the system)
CREATE TABLE IF NOT EXISTS advocates (
    advocate_id     VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    phone_number    VARCHAR(15) NOT NULL,
    email           VARCHAR(100),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Clients (advocate's clients)
CREATE TABLE IF NOT EXISTS clients (
    client_id                   VARCHAR(50) PRIMARY KEY,
    advocate_id                 VARCHAR(50) REFERENCES advocates(advocate_id),
    name                        VARCHAR(100) NOT NULL,
    phone_number                VARCHAR(15) NOT NULL,
    whatsapp_active             BOOLEAN DEFAULT TRUE,
    language_preference         VARCHAR(20) DEFAULT 'tamil',  -- tamil/hindi/english/tanglish
    opted_out                   BOOLEAN DEFAULT FALSE,
    opted_out_at                TIMESTAMP,
    first_message_sent          BOOLEAN DEFAULT FALSE,
    first_message_confirmed     BOOLEAN DEFAULT FALSE,
    created_at                  TIMESTAMP DEFAULT NOW()
);

-- Cases (every tracked court case)
CREATE TABLE IF NOT EXISTS cases (
    case_id                     SERIAL PRIMARY KEY,
    case_number                 VARCHAR(50) UNIQUE NOT NULL,  -- CNR number
    court_name                  VARCHAR(100),
    case_type                   VARCHAR(50),
    advocate_id                 VARCHAR(50) REFERENCES advocates(advocate_id),
    client_id                   VARCHAR(50) REFERENCES clients(client_id),
    status                      VARCHAR(20) DEFAULT 'active',  -- active/disposed/paused
    last_known_next_date        DATE,
    last_known_order_date       DATE,
    last_known_order_pdf        VARCHAR(255),
    last_known_status           VARCHAR(100),
    last_known_judge            VARCHAR(100),
    last_known_hall             VARCHAR(20),
    last_checked_at             TIMESTAMP,
    created_at                  TIMESTAMP DEFAULT NOW()
);

-- Events (every change detected by Watcher)
CREATE TABLE IF NOT EXISTS events (
    event_id                SERIAL PRIMARY KEY,
    case_id                 INTEGER REFERENCES cases(case_id),
    case_number             VARCHAR(50) NOT NULL,
    event_type              VARCHAR(50) NOT NULL,  -- NEW_DATE, NEW_ORDER, etc.
    event_detected_at       TIMESTAMP DEFAULT NOW(),
    old_value               TEXT,
    new_value               TEXT,
    pdf_url                 VARCHAR(500),
    less_than_24_hours      BOOLEAN DEFAULT FALSE,
    passed_to_reasoner_at   TIMESTAMP,
    reasoner_response       TEXT
);

-- Messages (every WhatsApp/SMS sent and received by Communicator)
CREATE TABLE IF NOT EXISTS messages (
    message_id          SERIAL PRIMARY KEY,
    case_id             INTEGER REFERENCES cases(case_id),
    client_id           VARCHAR(50) REFERENCES clients(client_id),
    message_type        VARCHAR(50) NOT NULL,   -- HEARING_REMINDER, ORDER_SUMMARY, etc.
    language            VARCHAR(20) NOT NULL,
    content_sent        TEXT NOT NULL,
    sent_at             TIMESTAMP DEFAULT NOW(),
    delivery_status     VARCHAR(20) DEFAULT 'sent',  -- sent/delivered/read/failed
    reply_received      BOOLEAN DEFAULT FALSE,
    reply_text          TEXT,
    reply_classified_as VARCHAR(30),            -- CONFIRMED/CANNOT_ATTEND/etc.
    reply_received_at   TIMESTAMP
);

-- API Failure Logs (for Supervisor Agent alerts)
CREATE TABLE IF NOT EXISTS api_failure_logs (
    log_id          SERIAL PRIMARY KEY,
    case_number     VARCHAR(50),
    api_used        VARCHAR(50),   -- ecourts/phoenix/vakeel360
    failure_reason  TEXT,
    failed_at       TIMESTAMP DEFAULT NOW(),
    resolved_at     TIMESTAMP
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_cases_status        ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_case_number   ON cases(case_number);
CREATE INDEX IF NOT EXISTS idx_events_case_id      ON events(case_id);
CREATE INDEX IF NOT EXISTS idx_messages_client_id  ON messages(client_id);
CREATE INDEX IF NOT EXISTS idx_clients_phone       ON clients(phone_number);
