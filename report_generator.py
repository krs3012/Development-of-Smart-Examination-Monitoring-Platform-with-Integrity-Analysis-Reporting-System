"""
report_generator.py
MILESTONE 3 - AI Summary Report Agent.

Generates a short, natural-language integrity report for a candidate's
exam session - the kind of write-up an LLM agent (e.g. via LangChain)
would produce, summarising their behaviour during the exam.

DESIGN NOTE: This is implemented as a rule-based template generator so it
works fully offline with no API key required - important for a reliable
live demo. The function signature and output (a single summary string)
are exactly what a real LLM call would also return, so replacing the body
of generate_report() with an actual LangChain + OpenAI/Anthropic call
later would not require changing anything else in the app - only this
one file.
"""

from scoring import compute_integrity_score


def generate_report(session_id, candidate_name="The candidate"):
    data = compute_integrity_score(session_id)

    score = data["score"]
    risk = data["risk_level"]
    tabs = data["tab_switch_count"]
    focus = data["focus_loss_count"]
    face_absent = data["total_face_absent_seconds"]

    lines = []
    lines.append(
        f"{candidate_name} completed the exam with an integrity score of {score}/100, "
        f"classified as {risk} risk."
    )

    if tabs == 0 and focus == 0 and face_absent < 5:
        lines.append(
            "No significant deviations were observed - the candidate remained "
            "focused and visible throughout the session."
        )
    else:
        notes = []
        if tabs > 0:
            notes.append(f"switched browser tabs {tabs} time{'s' if tabs != 1 else ''}")
        if focus > 0:
            notes.append(f"lost window focus {focus} time{'s' if focus != 1 else ''}")
        if face_absent >= 5:
            notes.append(f"was not visible on camera for a total of {int(face_absent)} seconds")

        if notes:
            if len(notes) > 1:
                joined = ", ".join(notes[:-1]) + f", and {notes[-1]}"
            else:
                joined = notes[0]
            lines.append(f"During the session, the candidate {joined}.")

    if risk == "Low":
        lines.append("This session does not require further review.")
    elif risk == "Medium":
        lines.append("This session shows some irregular activity and may warrant a brief manual review.")
    else:
        lines.append("This session shows significant irregular activity and is recommended for manual review by an invigilator.")

    return " ".join(lines)
