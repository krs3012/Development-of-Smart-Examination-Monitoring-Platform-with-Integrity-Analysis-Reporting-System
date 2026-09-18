"""
generate_data.py
WEEK 1 WARM-UP TASK.
This script uses the Faker library to create FAKE (synthetic) exam session
data - fake candidate names and fake event logs (tab switches, face-absent
seconds). This fake data will be used later, in Milestone 2 and 3, to build
and test the detection and scoring modules - before real webcam/browser data
is available.

Running this script creates a CSV file: synthetic_sessions.csv
"""

import csv
import random
from faker import Faker

fake = Faker()

NUM_CANDIDATES = 30  # how many fake exam sessions to generate
OUTPUT_FILE = "synthetic_sessions.csv"


def generate_synthetic_sessions(n=NUM_CANDIDATES):
    rows = []
    for i in range(1, n + 1):
        candidate_name = fake.name()
        candidate_email = fake.email()

        # Randomly simulate exam behaviour
        tab_switch_count = random.randint(0, 8)          # how many times they left the tab
        face_absent_seconds = random.randint(0, 400)     # total seconds face was missing
        focus_loss_count = random.randint(0, 10)          # how many times window lost focus
        session_duration_minutes = random.randint(30, 120)

        rows.append({
            "session_id": i,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "tab_switch_count": tab_switch_count,
            "face_absent_seconds": face_absent_seconds,
            "focus_loss_count": focus_loss_count,
            "session_duration_minutes": session_duration_minutes,
        })
    return rows


def save_to_csv(rows, filename=OUTPUT_FILE):
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created {filename} with {len(rows)} fake exam sessions.")


if __name__ == "__main__":
    sessions = generate_synthetic_sessions()
    save_to_csv(sessions)
