"""
camera_manager.py
MILESTONE 2 FIX.

Only ONE process should hold the webcam at a time - if the browser opens
its own camera stream AND the server also opens the camera separately,
one of them silently fails (this is what was happening).

This module is the SINGLE shared point of camera access. Both the live
video preview (streamed to the browser) and the face-presence detector
read frames from here, protected by a lock so they don't clash.
"""

import cv2
import threading

_camera = None
_lock = threading.Lock()


def open_camera():
    """Opens the webcam once. Safe to call multiple times."""
    global _camera
    with _lock:
        if _camera is None or not _camera.isOpened():
            _camera = cv2.VideoCapture(0)
    return _camera


def read_frame():
    """Reads one frame from the shared camera. Returns (success, frame)."""
    global _camera
    with _lock:
        if _camera is None or not _camera.isOpened():
            return False, None
        return _camera.read()


def release_camera():
    """Releases the webcam so other applications can use it again."""
    global _camera
    with _lock:
        if _camera is not None:
            _camera.release()
            _camera = None
