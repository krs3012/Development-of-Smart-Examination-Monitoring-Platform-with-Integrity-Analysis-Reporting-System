"""
face_monitor.py
Runs in a background thread for the whole exam duration, checking the
shared camera roughly once a second for face presence using OpenCV's
Haar Cascade detector, and logging intervals when the face is missing.
"""

import cv2
import time
import datetime
from database import get_connection
from camera_manager import read_frame

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
CHECK_INTERVAL_SECONDS = 1.0

# Live, real-time face status per session, so the browser can poll and show
# an on-screen warning the moment the face goes missing - not just after the
# exam ends. session_id -> {"face_present": bool, "missing_since": iso str or None}
live_status = {}


def monitor_face(session_id, stop_event):
    face_missing_since = None
    live_status[session_id] = {"face_present": True, "missing_since": None}

    while not stop_event.is_set():
        ret, frame = read_frame()

        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = FACE_CASCADE.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            face_present = len(faces) > 0

            if not face_present and face_missing_since is None:
                face_missing_since = datetime.datetime.now()
            elif face_present and face_missing_since is not None:
                _save_absence_interval(session_id, face_missing_since, datetime.datetime.now())
                face_missing_since = None

            live_status[session_id] = {
                "face_present": face_present,
                "missing_since": face_missing_since.isoformat() if face_missing_since else None,
            }

        time.sleep(CHECK_INTERVAL_SECONDS)

    if face_missing_since is not None:
        _save_absence_interval(session_id, face_missing_since, datetime.datetime.now())

    live_status.pop(session_id, None)


def _save_absence_interval(session_id, start, end):
    duration = (end - start).total_seconds()
    conn = get_connection()
    conn.execute(
        "INSERT INTO face_absence_log (session_id, start_time, end_time, duration_seconds) VALUES (?, ?, ?, ?)",
        (session_id, start.isoformat(), end.isoformat(), duration),
    )
    conn.commit()
    conn.close()
    print(f"[face_monitor] session {session_id}: face absent for {duration:.1f}s")
