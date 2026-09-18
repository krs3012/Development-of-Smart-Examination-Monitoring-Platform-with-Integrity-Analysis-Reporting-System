"""
rules_engine.py
MILESTONE 2 - Module 4: Suspicious Event Detection Engine.

Reads everything logged for one exam session (tab switches, focus-loss
events, total face-absent time) and checks it against simple, adjustable
thresholds. This is intentionally simple ("rule-based") - Milestone 3 will
replace/extend this with a proper weighted integrity SCORE. This module
just answers: "should this session be flagged for review, and why?"
"""

from database import get_connection

# ---- Configurable thresholds (from the project spec) ----
MAX_TAB_SWITCHES = 3
MAX_FACE_ABSENT_SECONDS = 120   # 2 minutes total across the session
MAX_FOCUS_LOSS_COUNT = 5


def evaluate_session(session_id):
    conn = get_connection()

    tab_switch_count = conn.execute(
        "SELECT COUNT(*) AS c FROM events WHERE session_id = ? AND event_type = 'tab_switch'",
        (session_id,),
    ).fetchone()["c"]

    focus_loss_count = conn.execute(
        "SELECT COUNT(*) AS c FROM events WHERE session_id = ? AND event_type = 'focus_loss'",
        (session_id,),
    ).fetchone()["c"]

    total_face_absent = conn.execute(
        "SELECT COALESCE(SUM(duration_seconds), 0) AS total FROM face_absence_log WHERE session_id = ?",
        (session_id,),
    ).fetchone()["total"]

    conn.close()

    flags = []
    if tab_switch_count > MAX_TAB_SWITCHES:
        flags.append(f"Excessive tab switches ({tab_switch_count} > {MAX_TAB_SWITCHES})")
    if total_face_absent > MAX_FACE_ABSENT_SECONDS:
        flags.append(f"Face absent too long ({int(total_face_absent)}s > {MAX_FACE_ABSENT_SECONDS}s)")
    if focus_loss_count > MAX_FOCUS_LOSS_COUNT:
        flags.append(f"Excessive focus loss ({focus_loss_count} > {MAX_FOCUS_LOSS_COUNT})")

    return {
        "tab_switch_count": tab_switch_count,
        "focus_loss_count": focus_loss_count,
        "total_face_absent_seconds": round(total_face_absent, 1),
        "flags": flags,
        "is_suspicious": len(flags) > 0,
    }
