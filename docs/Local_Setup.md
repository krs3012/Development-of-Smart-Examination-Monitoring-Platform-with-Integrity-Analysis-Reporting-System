# ExamGuard - Local Setup

## 1. Create the local environment file

Copy `.env.example` to `.env`. Then replace the example values with your own values:

```text
SECRET_KEY=your-private-secret
INVIGILATOR_EMAIL=your-invigilator-email
INVIGILATOR_PASSWORD=your-private-password
```

Keep `.env` only on your local computer. It is ignored by Git.

## 2. Install dependencies

```text
pip install -r requirements.txt
```

## 3. Start the application

```text
python app.py
```

Open the candidate login page at:

```text
http://127.0.0.1:5000/login
```

Open the invigilator login page at:

```text
http://127.0.0.1:5000/invigilator/login
```

## 4. Access rules

- Candidates can use registration, login, exam monitoring, and their own submitted report.
- Invigilators can use analytics, clustering, evidence, all submitted-session reports, and CSV/JSON export.
- Candidate and invigilator sessions are separated by role.
