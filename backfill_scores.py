"""
backfill_scores.py
ONE-TIME UTILITY - run this once after adding Milestone 3.

Finds any submitted exam sessions that don't have an integrity score yet
(created before the scoring feature existed) and computes + saves a score,
risk level, and AI report for each of them, so the analytics table shows
real numbers for every session instead of "None/100".

Usage: just run "python backfill_scores.py" once. Safe to run again later -
it only touches sessions that are still missing a score.
"""

from database import get_connection, init_db
from scoring import compute_integrity_score
from report_generator import generate_report


def backfill():
    init_db()  # make sure the score columns exist
    conn = get_connection()

    rows = conn.execute("""
        SELECT s.id AS session_id, c.name AS candidate_name
        FROM exam_sessions s
        JOIN candidates c ON c.id = s.candidate_id
        WHERE s.status = 'submitted' AND s.integrity_score IS NULL
    """).fetchall()

    if not rows:
        print("Nothing to backfill - every submitted session already has a score.") 
        conn.close()
        return

    print(f"Found {len(rows)} session(s) missing a score. Scoring now...")

    for row in rows:
        session_id = row["session_id"]
        candidate_name = row["candidate_name"]

        score_data = compute_integrity_score(session_id)
        report_text = generate_report(session_id, candidate_name=candidate_name)

        conn.execute(
            "UPDATE exam_sessions SET integrity_score = ?, risk_level = ?, ai_report = ? WHERE id = ?",
            (score_data["score"], score_data["risk_level"], report_text, session_id),
        )
        print(f"  - {candidate_name}: {score_data['score']}/100 ({score_data['risk_level']} risk)")

    conn.commit()
    conn.close()
    print("Backfill complete.")


if __name__ == "__main__":
    backfill()
