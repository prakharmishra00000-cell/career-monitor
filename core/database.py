import sqlite3
import os
from datetime import datetime, date
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "automator.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE NOT NULL,
                post_url TEXT,
                recruiter_name TEXT,
                recruiter_profile_url TEXT,
                post_text TEXT,
                job_type TEXT,
                is_paid INTEGER DEFAULT 1,
                domain_detected TEXT,
                relevance_score REAL DEFAULT 0.0,
                recruiter_instructions TEXT,
                whatsapp_number TEXT,
                requires_comment INTEGER DEFAULT 0,
                comment_text TEXT,
                pitch_message TEXT,
                connection_note TEXT,
                whatsapp_pitch TEXT,
                status TEXT DEFAULT 'DISCOVERED',
                comment_status TEXT DEFAULT 'NONE',
                whatsapp_status TEXT DEFAULT 'NONE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_leads_post_id ON leads(post_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        """)
        conn.commit()

def is_post_processed(post_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM leads WHERE post_id = ?", (post_id,))
        return cursor.fetchone() is not None

def insert_lead(lead_data: Dict[str, Any]) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leads (
                post_id, post_url, recruiter_name, recruiter_profile_url, post_text,
                job_type, is_paid, domain_detected, relevance_score, recruiter_instructions,
                whatsapp_number, requires_comment, comment_text, pitch_message,
                connection_note, whatsapp_pitch, status, comment_status, whatsapp_status, updated_at
            ) VALUES (
                :post_id, :post_url, :recruiter_name, :recruiter_profile_url, :post_text,
                :job_type, :is_paid, :domain_detected, :relevance_score, :recruiter_instructions,
                :whatsapp_number, :requires_comment, :comment_text, :pitch_message,
                :connection_note, :whatsapp_pitch, :status, :comment_status, :whatsapp_status, CURRENT_TIMESTAMP
            )
        """, lead_data)
        conn.commit()
        return cursor.lastrowid

def update_lead_status(lead_id: int, status: str, details: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (status, lead_id))
        conn.commit()
        if details:
            log_activity(lead_id, action_type=status, status="SUCCESS", details=details)

def update_comment_status(lead_id: int, comment_status: str, details: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads 
            SET comment_status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (comment_status, lead_id))
        conn.commit()
        if details:
            log_activity(lead_id, action_type="COMMENT", status=comment_status, details=details)

def update_whatsapp_status(lead_id: int, whatsapp_status: str, details: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads 
            SET whatsapp_status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (whatsapp_status, lead_id))
        conn.commit()
        if details:
            log_activity(lead_id, action_type="WHATSAPP", status=whatsapp_status, details=details)

def get_pending_connection_leads() -> List[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM leads 
            WHERE status = 'CONNECTION_REQUESTED'
            ORDER BY created_at ASC
        """)
        return cursor.fetchall()

def get_pending_whatsapp_leads() -> List[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM leads 
            WHERE whatsapp_status = 'PENDING' AND whatsapp_number IS NOT NULL AND is_paid = 1
            ORDER BY created_at ASC
        """)
        return cursor.fetchall()

def get_pending_comment_leads() -> List[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM leads 
            WHERE comment_status = 'PENDING' AND requires_comment = 1 AND is_paid = 1
            ORDER BY created_at ASC
        """)
        return cursor.fetchall()

def log_activity(lead_id: Optional[int], action_type: str, status: str, details: str = ""):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_log (lead_id, action_type, status, details, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (lead_id, action_type, status, details))
        conn.commit()

def get_daily_action_count(action_type: str) -> int:
    today_str = date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM activity_log 
            WHERE action_type = ? AND status = 'SUCCESS' AND date(created_at) = date(?)
        """, (action_type, today_str))
        count = cursor.fetchone()[0]
        return count

def get_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
        status_counts = dict(cursor.fetchall())
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_leads = cursor.fetchone()[0]
        return {
            "total_leads": total_leads,
            "status_breakdown": status_counts
        }
