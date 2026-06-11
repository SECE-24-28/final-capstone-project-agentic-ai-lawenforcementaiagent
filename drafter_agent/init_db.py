import os
import psycopg2
from dotenv import load_dotenv
import logging

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
-- 1. Create the cases table
CREATE TABLE IF NOT EXISTS cases (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    client_name VARCHAR(255),
    court_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Create the orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(id) ON DELETE CASCADE,
    order_date DATE,
    order_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Create the filings table
CREATE TABLE IF NOT EXISTS filings (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(id) ON DELETE CASCADE,
    filing_type VARCHAR(100),
    content TEXT,
    filed_by VARCHAR(100), -- e.g., 'petitioner', 'opponent'
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Create the documents table (for Drafter Agent)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50), 
    document_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL, -- Originally text, later can be a Cloudinary URL
    edited_content TEXT,
    approval_status VARCHAR(50) DEFAULT 'pending',
    lawyer_approval_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

def initialize_database():
    try:
        print(f"Connecting to Postgres using URL: {DATABASE_URL}")
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLES_SQL)
            conn.commit()
        print("Database schema successfully created!")
    except Exception as e:
        print(f"Error creating database schema: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    initialize_database()
