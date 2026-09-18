"""
database.py
Creates the database and gives helper functions to talk to it.

Tables:
- candidates: registered students
- exam_sessions: tracks each candidate's exam state (not_started/in_progress/paused/submitted)
- events: browser-side events (tab switches, focus loss) with timestamps
- face_absence_log: intervals where the webcam did NOT see a face
"""

import sqlite3

DB_NAME = "exam.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            photo_path TEXT,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            status TEXT DEFAULT 'not_started',
            started_at TEXT,
            submitted_at TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_time TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES exam_sessions (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS face_absence_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_seconds REAL,
            FOREIGN KEY (session_id) REFERENCES exam_sessions (id)
        )
    """)

    # Milestone 4: evidence screenshots captured at the moment of suspicious events
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES exam_sessions (id)
        )
    """)

    # Milestone 3: add scoring columns to exam_sessions if they don't exist yet.
    existing_cols = [row["name"] for row in cur.execute("PRAGMA table_info(exam_sessions)").fetchall()]
    if "integrity_score" not in existing_cols:
        cur.execute("ALTER TABLE exam_sessions ADD COLUMN integrity_score REAL")
    if "risk_level" not in existing_cols:
        cur.execute("ALTER TABLE exam_sessions ADD COLUMN risk_level TEXT")
    if "ai_report" not in existing_cols:
        cur.execute("ALTER TABLE exam_sessions ADD COLUMN ai_report TEXT")

    conn.commit()
    conn.close()
    print("Database ready: candidates, exam_sessions, events, face_absence_log tables created.")


if __name__ == "__main__":
    init_db()
