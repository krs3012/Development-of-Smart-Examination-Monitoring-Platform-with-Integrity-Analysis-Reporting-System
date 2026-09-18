"""
scoring.py
MILESTONE 3 - Integrity Scoring Engine.

Turns the raw monitoring data collected in Milestone 2 (tab switches,
focus-loss events, total face-absent time) into a single WEIGHTED SCORE
from 0 (worst) to 100 (best), plus a Low / Medium / High risk band.

This replaces the simple "flagged / not flagged" logic from the
Milestone 2 rules engine with something more nuanced and presentable.
"""

from database import get_connection

BASE_SCORE = 100  # every session starts "clean"

# ---- Penalty weights (points deducted per occurrence) ----
PENALTY_PER_TAB_SWITCH = 5
PENALTY_PER_FOCUS_LOSS = 3
PENALTY_PER_10S_FACE_ABSENT = 2  # 2 points lost for every 10 seconds face was missing


def compute_integrity_score(session_id):
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

    tab_penalty = tab_switch_count * PENALTY_PER_TAB_SWITCH
    focus_penalty = focus_loss_count * PENALTY_PER_FOCUS_LOSS
    face_penalty = (total_face_absent / 10) * PENALTY_PER_10S_FACE_ABSENT

    raw_score = BASE_SCORE - tab_penalty - focus_penalty - face_penalty
    score = max(0, min(100, round(raw_score)))

    if score >= 80:
        risk_level = "Low"
    elif score >= 50:
        risk_level = "Medium"
    else:
        risk_level = "High"

    return {
        "score": score,
        "risk_level": risk_level,
        "tab_switch_count": tab_switch_count,
        "focus_loss_count": focus_loss_count,
        "total_face_absent_seconds": round(total_face_absent, 1),
        "breakdown": {
            "tab_switch_penalty": tab_penalty,
            "focus_loss_penalty": focus_penalty,
            "face_absent_penalty": round(face_penalty, 1),
        },
    }
