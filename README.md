# ExamGuard - Online Exam Monitoring & Integrity Analytics Platform

A Flask-based web application that monitors candidates during online exams and produces integrity analytics based on their behavior — built as part of Infosys Virtual Internship 7.0.

## Overview

ExamGuard lets a candidate register, log in, and take an exam while the system monitors their behavior in real time through the webcam and browser. After submission, the system calculates a weighted integrity score, generates a natural-language summary report, captures evidence of any flagged events, and gives an invigilator a consolidated analytics view across all candidates.

## Features

- **Registration & Login** - candidates register with a live camera preview and manually capture their own photo before submitting details
- **Real-Time Monitoring** - once the exam begins, the candidate sees their own live camera feed; in the background, the system checks for face presence roughly once a second using OpenCV's Haar Cascade classifier, while JavaScript detects browser tab switches and window focus loss
- **On-Screen Warnings** - the candidate sees instant warning popups for tab switches or focus loss, and a persistent banner while their face is not visible - creating real-time awareness rather than silent logging
- **Integrity Scoring** - every session starts at 100 points; points are deducted for tab switches, focus loss, and face-absent time, producing a Low / Medium / High risk classification
- **AI-Style Report** - a natural-language summary of the candidate's behavior is generated automatically (rule-based, so it works reliably without a live API dependency during a demo)
- **Evidence Management** - a screenshot is captured at the exact moment of every tab-switch or focus-loss event
- **Analytics & Clustering** - a batch-level analytics table plus K-Means clustering that groups candidates into Low / Moderate / High Activity clusters based on combined behavior
- **Consolidated Report & Export** - a printable, consolidated report per candidate (score, AI summary, events, evidence, cluster), plus CSV/JSON export of all submitted sessions
- **Invigilator Access Control** - analytics, clustering, and exports are restricted to a separate invigilator login; candidates can only view their own individual report

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite
- **Computer Vision:** OpenCV (Haar Cascade face detection)
- **Machine Learning:** scikit-learn (K-Means clustering)
- **Frontend:** HTML, CSS, JavaScript
- **Testing Data:** Faker (synthetic session data generator)

## Project Structure

```
examguard/
  app.py                   Main Flask app - routes and request handling
  database.py               SQLite setup (candidates, exam_sessions, events,
                             face_absence_log, evidence, invigilators tables)
  camera_manager.py         Single shared webcam access point
  face_monitor.py           Background thread: continuous face-presence detection
  rules_engine.py           Threshold-based flagging
  scoring.py                 Weighted 0-100 integrity scoring engine
  report_generator.py       Natural-language summary report generator
  clustering.py              K-Means behavioral clustering across all candidates
  backfill_scores.py         One-time utility to score sessions predating scoring
  generate_data.py           Synthetic test data generator (Faker)
  requirements.txt
  static/
    photos/                  Registration photos
    evidence/                 Event-triggered screenshots
  templates/
    login.html, register.html, dashboard.html, exam.html,
    analytics.html, clustering.html, evidence.html, report.html,
    invigilator_login.html
docs/
  Project_Documentation.md
  Agile_Template_ExamGuard.xlsx
  Defect_Tracker_ExamGuard.xlsx
  Unit_Test_Plan_ExamGuard.xlsx
```

## Setup & Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create your local environment file (never committed to Git):
```bash
cp .env.example .env
```
Then edit `.env` and set your own values:
```
SECRET_KEY=your-private-secret
INVIGILATOR_EMAIL=your-invigilator-email
INVIGILATOR_PASSWORD=your-private-password
```

3. Run the app:
```bash
python app.py
```

Then open `http://127.0.0.1:5000` in a browser.

**Invigilator login** uses the email/password you set in your own `.env` file — there is no default account, since credentials are kept out of the public repository.

**Note:** candidate passwords are stored as secure hashes (not plain text). If you have an older local database from before this change, delete `exam.db` and re-register test candidates, since old plaintext passwords are no longer compatible.

## Notes

- The database (`exam.db`) is created and upgraded automatically on startup.
- The Flask server runs with `threaded=True` since the live video stream holds one connection open continuously.
- K-Means clustering requires at least 3 submitted sessions to produce meaningful groups.

## Author

Rohini Sai Kuchipudi
