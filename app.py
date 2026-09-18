from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, abort
from werkzeug.security import generate_password_hash, check_password_hash
import cv2
import os
import csv
import io
import json
import threading
import datetime
import hmac
from functools import wraps
from database import get_connection, init_db
from face_monitor import monitor_face, live_status
from rules_engine import evaluate_session
from scoring import compute_integrity_score
from report_generator import generate_report
from clustering import run_clustering
import camera_manager

def _load_local_env(path=".env"):
    """Load simple KEY=VALUE pairs from a local .env file if present.

    This keeps the student project dependency-free while allowing local
    secrets/configuration to stay outside the Git repository.
    """
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except OSError:
        pass


_load_local_env()

app = Flask(__name__)
# Use a private environment value when supplied; otherwise generate a local-only key.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

INVIGILATOR_EMAIL = os.environ.get("INVIGILATOR_EMAIL", "").strip().lower()
INVIGILATOR_PASSWORD = os.environ.get("INVIGILATOR_PASSWORD", "")

PHOTO_FOLDER = "static/photos"
EVIDENCE_FOLDER = "static/evidence"
os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(EVIDENCE_FOLDER, exist_ok=True)

active_monitors = {}


@app.context_processor
def inject_role_flags():
    return {"is_invigilator": session.get("role") == "invigilator"}


def candidate_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "candidate" or "candidate_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def invigilator_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "invigilator":
            return redirect(url_for("invigilator_login"))
        return view_func(*args, **kwargs)

    return wrapper


def report_access_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("role") == "invigilator":
            return view_func(*args, **kwargs)

        if session.get("role") != "candidate" or "candidate_id" not in session:
            return redirect(url_for("login"))

        session_id = kwargs.get("session_id")
        conn = get_connection()
        row = conn.execute(
            "SELECT candidate_id FROM exam_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        conn.close()

        if not row or row["candidate_id"] != session["candidate_id"]:
            abort(403)

        return view_func(*args, **kwargs)

    return wrapper


# ---------- HOME ----------
@app.route("/")
def home():
    if session.get("role") == "invigilator":
        return redirect(url_for("analytics"))
    if session.get("role") == "candidate":
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------- INVIGILATOR LOGIN ----------
@app.route("/invigilator/login", methods=["GET", "POST"])
def invigilator_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not INVIGILATOR_EMAIL or not INVIGILATOR_PASSWORD:
            flash("Invigilator credentials are not configured. Set INVIGILATOR_EMAIL and INVIGILATOR_PASSWORD in .env.")
            return redirect(url_for("invigilator_login"))

        valid_email = hmac.compare_digest(email, INVIGILATOR_EMAIL)
        valid_password = hmac.compare_digest(password, INVIGILATOR_PASSWORD)

        if valid_email and valid_password:
            session.clear()
            session["role"] = "invigilator"
            session["invigilator_email"] = email
            return redirect(url_for("analytics"))

        flash("Invalid invigilator email or password.")
        return redirect(url_for("invigilator_login"))

    return render_template("invigilator_login.html")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        pending_photo = request.form.get("pending_photo")

        if pending_photo:
            final_filename = f"{email.replace('@', '_at_')}.jpg"
            src = os.path.join(PHOTO_FOLDER, pending_photo)
            dst = os.path.join(PHOTO_FOLDER, final_filename)
            if os.path.exists(src):
                os.replace(src, dst)
                photo_filename = final_filename
            else:
                photo_filename = None
        else:
            photo_filename = capture_photo(email)

        camera_manager.release_camera()

        conn = get_connection()
        try:
            password_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO candidates (name, email, password, photo_path) VALUES (?, ?, ?, ?)",
                (name, email, password_hash, photo_filename),
            )
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Registration failed: could this email already exist? ({e})")
            return redirect(url_for("register"))
        finally:
            conn.close()

    camera_manager.open_camera()
    return render_template("register.html")


@app.route("/capture_photo_ajax", methods=["POST"])
def capture_photo_ajax():
    ret, frame = camera_manager.read_frame()
    if not ret:
        return jsonify({"ok": False, "error": "camera not available"}), 400

    import uuid
    temp_filename = f"tmp_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(PHOTO_FOLDER, temp_filename)
    cv2.imwrite(filepath, frame)

    return jsonify({"ok": True, "filename": temp_filename})


def capture_photo(email):
    filename = f"{email.replace('@', '_at_')}.jpg"
    filepath = os.path.join(PHOTO_FOLDER, filename)

    cam = cv2.VideoCapture(0)
    ret = False
    frame = None
    for _ in range(30):
        ret, frame = cam.read()
    if ret:
        cv2.imwrite(filepath, frame)
    cam.release()

    return filename if ret else None


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        candidate = conn.execute(
            "SELECT * FROM candidates WHERE email = ?",
            (email,),
        ).fetchone()
        conn.close()

        if candidate and check_password_hash(candidate["password"], password):
            session.clear()
            session["role"] = "candidate"
            session["candidate_id"] = candidate["id"]
            session["candidate_name"] = candidate["name"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- DASHBOARD ----------
@app.route("/dashboard")
@candidate_required
def dashboard():
    if "candidate_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    exam_session = conn.execute(
        "SELECT * FROM exam_sessions WHERE candidate_id = ? ORDER BY id DESC LIMIT 1",
        (session["candidate_id"],),
    ).fetchone()
    conn.close()

    status = exam_session["status"] if exam_session else "not_started"

    summary = None
    score_info = None
    if exam_session and status == "submitted":
        summary = evaluate_session(exam_session["id"])
        score_info = {
            "score": exam_session["integrity_score"],
            "risk_level": exam_session["risk_level"],
            "ai_report": exam_session["ai_report"],
        }

    return render_template(
        "dashboard.html", name=session["candidate_name"], status=status, summary=summary, score_info=score_info,
        exam_session_id=exam_session["id"] if exam_session else None
    )


# ---------- ANALYTICS ----------
@app.route("/analytics")
@invigilator_required
def analytics():
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id AS session_id, c.name, c.email, s.integrity_score, s.risk_level, s.submitted_at
        FROM exam_sessions s
        JOIN candidates c ON c.id = s.candidate_id
        WHERE s.status = 'submitted'
        ORDER BY s.submitted_at DESC
    """).fetchall()
    conn.close()
    return render_template("analytics.html", rows=rows)


# ---------- EVIDENCE GALLERY (Milestone 4) ----------
@app.route("/evidence/<int:session_id>")
@invigilator_required
def view_evidence(session_id):
    conn = get_connection()
    session_row = conn.execute(
        "SELECT s.*, c.name AS candidate_name FROM exam_sessions s JOIN candidates c ON c.id = s.candidate_id WHERE s.id = ?",
        (session_id,),
    ).fetchone()

    evidence_rows = conn.execute(
        "SELECT * FROM evidence WHERE session_id = ? ORDER BY captured_at ASC",
        (session_id,),
    ).fetchall()
    conn.close()

    if not session_row:
        return "Session not found", 404

    return render_template("evidence.html", session=session_row, evidence=evidence_rows)


# ---------- FULL REPORT (Milestone 5: everything about one candidate in one view) ----------
@app.route("/report/<int:session_id>")
@report_access_required
def full_report(session_id):
    conn = get_connection()
    session_row = conn.execute("""
        SELECT s.*, c.name AS candidate_name, c.email AS candidate_email
        FROM exam_sessions s
        JOIN candidates c ON c.id = s.candidate_id
        WHERE s.id = ?
    """, (session_id,)).fetchone()

    if not session_row:
        conn.close()
        return "Session not found", 404

    if session_row["status"] != "submitted":
        conn.close()
        return "Report is available after exam submission.", 404

    evidence_rows = conn.execute(
        "SELECT * FROM evidence WHERE session_id = ? ORDER BY captured_at ASC",
        (session_id,),
    ).fetchall()
    conn.close()

    summary = evaluate_session(session_id)

    # Find this session's behavioral cluster, if enough sessions exist to form clusters
    cluster_label = None
    cluster_data = run_clustering()
    if cluster_data:
        for c in cluster_data:
            if c["session_id"] == session_id:
                cluster_label = c["cluster_label"]
                break

    return render_template(
        "report.html", session=session_row, evidence=evidence_rows, summary=summary, cluster_label=cluster_label
    )


# ---------- EXPORT (Milestone 5: batch data export) ----------
@app.route("/export/csv")
@invigilator_required
def export_csv():
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.name, c.email, s.integrity_score, s.risk_level, s.submitted_at
        FROM exam_sessions s JOIN candidates c ON c.id = s.candidate_id
        WHERE s.status = 'submitted'
        ORDER BY s.submitted_at DESC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Candidate Name", "Email", "Integrity Score", "Risk Level", "Submitted At"])
    for r in rows:
        writer.writerow([r["name"], r["email"], r["integrity_score"], r["risk_level"], r["submitted_at"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=examguard_report.csv"},
    )


@app.route("/export/json")
@invigilator_required
def export_json():
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.name, c.email, s.integrity_score, s.risk_level, s.submitted_at
        FROM exam_sessions s JOIN candidates c ON c.id = s.candidate_id
        WHERE s.status = 'submitted'
        ORDER BY s.submitted_at DESC
    """).fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    return Response(
        json.dumps(data, indent=2, default=str),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=examguard_report.json"},
    )

# ---------- BEHAVIORAL CLUSTERING (K-Means) ----------
@app.route("/clustering")
@invigilator_required
def clustering_view():
    data = run_clustering()
    return render_template("clustering.html", data=data)


# ---------- SESSION HELPERS ----------
def _get_or_create_session_id():
    conn = get_connection()
    existing = conn.execute(
        "SELECT * FROM exam_sessions WHERE candidate_id = ? ORDER BY id DESC LIMIT 1",
        (session["candidate_id"],),
    ).fetchone()

    if existing and existing["status"] != "submitted":
        session_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO exam_sessions (candidate_id, status) VALUES (?, 'not_started')",
            (session["candidate_id"],),
        )
        conn.commit()
        session_id = cur.lastrowid

    conn.close()
    return session_id


def _set_status(session_id, status, started=False, submitted=False):
    conn = get_connection()
    now = datetime.datetime.now().isoformat()
    conn.execute("UPDATE exam_sessions SET status = ? WHERE id = ?", (status, session_id))
    if started:
        conn.execute("UPDATE exam_sessions SET started_at = ? WHERE id = ?", (now, session_id))
    if submitted:
        conn.execute("UPDATE exam_sessions SET submitted_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()


# ---------- START EXAM ----------
@app.route("/session/start")
@candidate_required
def start_session():
    if "candidate_id" not in session:
        return redirect(url_for("login"))

    session_id = _get_or_create_session_id()
    _set_status(session_id, "in_progress", started=True)
    session["exam_session_id"] = session_id

    camera_manager.open_camera()

    if session_id not in active_monitors:
        stop_event = threading.Event()
        thread = threading.Thread(target=monitor_face, args=(session_id, stop_event), daemon=True)
        thread.start()
        active_monitors[session_id] = {"thread": thread, "stop_event": stop_event}

    return redirect(url_for("exam_page"))


@app.route("/video_feed")
@candidate_required
def video_feed():
    def generate():
        while True:
            ret, frame = camera_manager.read_frame()
            if not ret:
                continue
            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            frame_bytes = buffer.tobytes()
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/exam")
@candidate_required
def exam_page():
    if "candidate_id" not in session:
        return redirect(url_for("login"))
    return render_template("exam.html", name=session["candidate_name"])


# ---------- LIVE FACE STATUS (polled by exam page to show real-time warnings) ----------
@app.route("/face_status")
@candidate_required
def face_status():
    if "exam_session_id" not in session:
        return jsonify({"face_present": True, "missing_seconds": 0})

    status = live_status.get(session["exam_session_id"])
    if not status:
        return jsonify({"face_present": True, "missing_seconds": 0})

    missing_seconds = 0
    if status["missing_since"]:
        missing_since = datetime.datetime.fromisoformat(status["missing_since"])
        missing_seconds = (datetime.datetime.now() - missing_since).total_seconds()

    return jsonify({"face_present": status["face_present"], "missing_seconds": round(missing_seconds, 1)})


@app.route("/log_event", methods=["POST"])
@candidate_required
def log_event():
    if "exam_session_id" not in session:
        return jsonify({"ok": False, "error": "no active session"}), 400

    data = request.get_json()
    event_type = data.get("event_type")
    if event_type not in ("tab_switch", "focus_loss"):
        return jsonify({"ok": False, "error": "invalid event_type"}), 400

    session_id = session["exam_session_id"]
    now = datetime.datetime.now()

    conn = get_connection()
    conn.execute(
        "INSERT INTO events (session_id, event_type, event_time) VALUES (?, ?, ?)",
        (session_id, event_type, now.isoformat()),
    )
    conn.commit()

    # Milestone 4: capture a snapshot from the shared camera at this exact moment,
    # as evidence to review later - only if the camera is currently available
    # (e.g. tab-switch happens while the browser tab is hidden, so a snapshot
    # taken right as it happens may not always succeed, which is fine).
    ret, frame = camera_manager.read_frame()
    if ret:
        import uuid
        evidence_filename = f"evid_{session_id}_{uuid.uuid4().hex[:6]}.jpg"
        evidence_path = os.path.join(EVIDENCE_FOLDER, evidence_filename)
        cv2.imwrite(evidence_path, frame)
        conn.execute(
            "INSERT INTO evidence (session_id, event_type, photo_path, captured_at) VALUES (?, ?, ?, ?)",
            (session_id, event_type, evidence_filename, now.isoformat()),
        )
        conn.commit()

    conn.close()
    return jsonify({"ok": True})


@app.route("/session/pause")
@candidate_required
def pause_session():
    if "exam_session_id" in session:
        _set_status(session["exam_session_id"], "paused")
    return redirect(url_for("dashboard"))


@app.route("/session/submit")
@candidate_required
def submit_session():
    if "exam_session_id" in session:
        session_id = session["exam_session_id"]
        _set_status(session_id, "submitted", submitted=True)

        monitor = active_monitors.pop(session_id, None)
        if monitor:
            monitor["stop_event"].set()
            monitor["thread"].join(timeout=3)

        camera_manager.release_camera()

        score_data = compute_integrity_score(session_id)
        report_text = generate_report(session_id, candidate_name=session.get("candidate_name", "The candidate"))

        conn = get_connection()
        conn.execute(
            "UPDATE exam_sessions SET integrity_score = ?, risk_level = ?, ai_report = ? WHERE id = ?",
            (score_data["score"], score_data["risk_level"], report_text, session_id),
        )
        conn.commit()
        conn.close()

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False, threaded=True)
