# ExamGuard - Project Documentation

## 1. Introduction

ExamGuard is an online exam monitoring and integrity analytics platform developed with Python and Flask. The application collects selected examination-behaviour information, stores the data in SQLite, and analyses the submitted session to produce an integrity score, risk level, report, evidence view, analytics, and behavioural clusters.

## 2. Problem Statement

Online examinations make it difficult to observe candidate behaviour continuously. Events such as leaving the exam tab, losing window focus, or being absent from the camera may be useful signals for later review. ExamGuard provides a structured way to capture these signals and present them together with the final examination session information.

## 3. Objectives

1. Monitor candidate activity during an online examination.
2. Detect supported browser activity events.
3. Monitor face presence using the webcam.
4. Store events and face-absence intervals with timestamps.
5. Calculate an integrity score and risk level.
6. Generate a natural-language integrity summary.
7. Group submitted sessions using K-Means clustering.
8. Preserve event evidence where a camera frame can be captured.
9. Provide reports and exportable session summaries.

## 4. Scope

The current implementation covers candidate registration, webcam photo capture, credential login, examination session management, camera streaming, face-presence monitoring, browser tab/focus event logging, evidence capture attempts, rule-based evaluation, weighted scoring, automatic report generation, analytics, K-Means clustering, and CSV/JSON export.

## 5. Proposed System

The proposed system combines monitoring data from two sources:

- Webcam-based face presence monitoring.
- Browser-side examination activity monitoring.

The collected information is stored in SQLite and processed after submission. The scoring engine calculates the integrity score, while the report generator produces a natural-language summary. The clustering module analyses submitted sessions together to identify behavioural groups.

For access control, the application separates candidate and invigilator roles. Candidates can access their own examination workflow and their own report. Invigilators use a separate login and can access submitted-session analytics, clustering, evidence, reports, and data exports. Invigilator credentials are configured locally through `.env` and are excluded from GitHub.

## 6. System Architecture

```text
Browser / Candidate
        │
        ├── Registration + Login
        ├── Exam Page
        └── Browser Events
                │
                ▼
          Flask Application
                │
        ┌───────┼────────┐
        ▼       ▼        ▼
   Camera    Event     Session
   Manager   Logger    Management
        │       │        │
        ▼       └────┬───┘
   Face Monitor       │
        │             ▼
        └──────►   SQLite
                     │
          ┌──────────┼───────────┐
          ▼          ▼           ▼
       Scoring    Reporting   Clustering
          │          │           │
          └──────────┼───────────┘
                     ▼
              Dashboard / Report
              Analytics / Export
```

## 7. Modules

### 7.1 `app.py`

Main Flask application. It handles registration, login, dashboard, examination session lifecycle, video streaming, browser event logging, evidence capture, reporting, analytics, clustering, and export routes.

### 7.2 `database.py`

Creates and accesses the SQLite database. The schema contains candidates, exam sessions, events, face-absence logs, and evidence records.

### 7.3 `camera_manager.py`

Provides a shared webcam access point protected by a thread lock so the live video stream and face-monitoring thread can read from the same camera without competing for separate camera handles.

### 7.4 `face_monitor.py`

Runs a background thread during an active exam. It checks the shared camera approximately once per second using the OpenCV Haar Cascade classifier and records intervals when a face is not detected.

### 7.5 `rules_engine.py`

Checks session data against configurable thresholds and reports whether the session should be flagged for review.

### 7.6 `scoring.py`

Calculates a weighted integrity score from 0 to 100 using tab switches, focus loss, and face-absence duration. It also assigns a risk level.

### 7.7 `report_generator.py`

Generates a natural-language integrity report using project rules and the scoring result. The current implementation is rule-based and works without an external LLM API.

### 7.8 `clustering.py`

Uses Scikit-learn K-Means to group submitted sessions based on three behavioural features: tab-switch count, focus-loss count, and total face-absent seconds.

### 7.9 `generate_data.py`

Generates synthetic session data for development/testing purposes.

### 7.10 `backfill_scores.py`

Provides a utility for calculating missing scores for sessions created before scoring fields were added.

## 8. Database Design

The application uses SQLite.

### Candidates

Stores candidate registration information, including name, email, password, photo path, and registration time.

### Exam Sessions

Stores candidate exam-session state, start/submission times, integrity score, risk level, and generated report.

### Events

Stores browser-related event types and timestamps for each session.

### Face Absence Log

Stores the start time, end time, and duration of periods when a face was not detected.

### Evidence

Stores the session, event type, image path, and capture time for evidence frames successfully captured during supported events.

## 9. Monitoring Process

1. Candidate logs in.
2. Candidate starts the examination.
3. The shared camera is opened.
4. A background thread checks face presence approximately once per second.
5. Browser-side monitoring reports supported tab-switch and focus-loss events.
6. Events are saved with timestamps.
7. A camera frame is attempted as evidence when supported events are received.
8. Face-absence intervals are stored when the face becomes visible again or the exam ends.
9. The candidate submits the examination.

## 10. Integrity Scoring

The scoring engine starts each session at 100 points.

| Behaviour | Current penalty |
|---|---:|
| Tab switch | 5 points per event |
| Focus loss | 3 points per event |
| Face absence | 2 points per 10 seconds |

The final score is bounded between 0 and 100.

| Score | Risk level |
|---:|---|
| 80-100 | Low |
| 50-79 | Medium |
| 0-49 | High |

## 11. Rule-Based Evaluation

The separate rules engine currently uses these thresholds:

- More than 3 tab switches.
- More than 5 focus-loss events.
- More than 120 seconds of total face absence.

If one or more thresholds are exceeded, the session is marked suspicious by the rule-based evaluator.

## 12. Report Generation

After submission, the system calculates the integrity score and creates a natural-language summary. The report mentions the score, risk level, and detected behavioural activity. It also provides a manual-review recommendation according to the current project rules.

The current report generator is not a live LLM call.

## 13. K-Means Behavioural Clustering

K-Means is applied to all submitted sessions when at least three sessions are available for the default three clusters.

The input features are:

- Tab-switch count.
- Focus-loss count.
- Total face-absent seconds.

Cluster labels are mapped to Low Activity, Moderate Activity, and High Activity based on the total activity represented by each cluster centroid.

## 14. Role-Based Access Control

The application separates candidate and invigilator access. Candidates can access the examination workflow and view only their own submitted-session report. Invigilator authentication uses credentials configured locally in `.env`; those credentials are not stored in the repository. Invigilators can review submitted-session analytics, clustering, evidence, reports, and CSV/JSON exports.

A local setup guide is provided in `docs/Local_Setup.md` for creating the ignored `.env` file and starting the application.

## 15. Reports and Export

The project provides:

- Candidate-session report.
- Evidence gallery.
- Batch analytics table.
- K-Means clustering view.
- CSV export.
- JSON export.

## 16. Testing Plan

The application should be tested from registration through export:

1. Registration and webcam capture.
2. Login and dashboard.
3. Exam start and camera feed.
4. Face-present and face-absent conditions.
5. Tab-switch event.
6. Focus-loss event.
7. Evidence capture attempt.
8. Exam submission.
9. Score and risk calculation.
10. Report display.
11. Analytics.
12. Clustering.
13. CSV export.
14. JSON export.

## 17. Limitations

- Haar Cascade detects face presence and does not establish identity.
- Browser event detection depends on browser behaviour and page visibility/focus APIs.
- Evidence capture may fail if a camera frame is unavailable at the exact event time.
- The report generator is rule-based rather than a live LLM service.
- The application currently uses a Flask development server.

## 18. Future Enhancements

- Optional production-grade authentication and authorization.
- Optional LLM-based reporting.
- Face verification and anti-spoofing.
- Production database support.
- Automated unit/integration tests.
- Production deployment configuration.

## 19. Conclusion

ExamGuard provides a structured prototype for online examination monitoring and integrity analysis. It combines camera-based face-presence monitoring, browser event logging, evidence capture, rule-based evaluation, weighted scoring, automatic reporting, and K-Means behavioural clustering in one Flask application.
