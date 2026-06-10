import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise e

def save_document(case_id: str, document_type: str, content: str, client_content: str = None, language: str = None, court_format: str = None):
    """Saves a new document to the database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # We mock the split saving logic for ORDER_SUMMARY if needed here, 
            # or just assume the column structure is flexible.
            # Base inserts as per provided prompt queries
            cur.execute("""
                INSERT INTO documents (case_id, document_type, content, approval_status, created_at)
                VALUES (%s, %s, %s, 'pending', NOW())
                RETURNING id
            """, (case_id, document_type, content))
            doc_id = cur.fetchone()[0]
            conn.commit()
            return f"doc_{doc_id}"
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save document: {e}")
        raise e
    finally:
        conn.close()

def get_pending_documents():
    """Retrieves all documents waiting for lawyer approval."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, case_id, document_type, LEFT(content, 200) as preview, created_at
                FROM documents
                WHERE approval_status = 'pending'
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
            return rows
    except Exception as e:
        logger.error(f"Failed to get pending documents: {e}")
        raise e
    finally:
        conn.close()

def update_document_status(doc_id: str, status: str, edited_content: str = None):
    """Updates approval status and edits if available."""
    conn = get_db_connection()
    try:
        # doc_id is expected to be "doc_123", extract the ID 123
        db_id = int(doc_id.replace("doc_", ""))
        with conn.cursor() as cur:
            if edited_content:
                cur.execute("""
                    UPDATE documents
                    SET approval_status = %s, edited_content = %s, lawyer_approval_timestamp = NOW()
                    WHERE id = %s
                """, (status, edited_content, db_id))
            else:
                cur.execute("""
                    UPDATE documents
                    SET approval_status = %s, lawyer_approval_timestamp = NOW()
                    WHERE id = %s
                """, (status, db_id))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update document status: {e}")
        raise e
    finally:
        conn.close()

def get_document_by_id(doc_id: str):
    """Retrieves a specific document by its doc_id."""
    conn = get_db_connection()
    try:
        db_id = int(doc_id.replace("doc_", ""))
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM documents WHERE id = %s", (db_id,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise e
    finally:
        conn.close()

def get_case_history(case_id: str):
    """Fetches case history to provide context for document generation."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM cases
                LEFT JOIN orders ON cases.id = orders.case_id
                LEFT JOIN filings ON cases.id = filings.case_id
                WHERE cases.id = %s
                ORDER BY created_at DESC
            """, (case_id,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch case history: {e}")
        return []
    finally:
        conn.close()

def delete_document(doc_id: str):
    """Deletes a document from the database entirely."""
    conn = get_db_connection()
    try:
        db_id = int(doc_id.replace("doc_", ""))
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (db_id,))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete document: {e}")
        raise e
    finally:
        conn.close()
