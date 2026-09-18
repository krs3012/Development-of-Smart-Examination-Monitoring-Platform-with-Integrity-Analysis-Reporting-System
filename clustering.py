"""
clustering.py
MILESTONE 3 EXTENSION - Behavioral Clustering.

While scoring.py evaluates ONE candidate's session against fixed rules,
this module looks at ALL submitted candidates TOGETHER and groups them
into behavioral clusters using K-Means - an unsupervised machine learning
algorithm. This reveals patterns across the batch (e.g. "most candidates
behaved normally, a small group showed noticeably higher activity")
rather than judging each session in isolation.

Three features are used per candidate, all already collected during
monitoring: tab-switch count, focus-loss count, and total face-absent
seconds. K-Means groups candidates whose values are close together into
the same cluster.
"""

from sklearn.cluster import KMeans
import numpy as np
from database import get_connection


def get_session_features():
    """Pulls the 3 behavioral features for every submitted session."""
    conn = get_connection()
    sessions = conn.execute(
        "SELECT id, candidate_id FROM exam_sessions WHERE status = 'submitted'"
    ).fetchall()

    data = []
    for s in sessions:
        session_id = s["id"]

        tab_count = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE session_id = ? AND event_type = 'tab_switch'",
            (session_id,),
        ).fetchone()["c"]

        focus_count = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE session_id = ? AND event_type = 'focus_loss'",
            (session_id,),
        ).fetchone()["c"]

        face_absent = conn.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) AS total FROM face_absence_log WHERE session_id = ?",
            (session_id,),
        ).fetchone()["total"]

        candidate = conn.execute(
            "SELECT name, email FROM candidates WHERE id = ?", (s["candidate_id"],)
        ).fetchone()

        data.append({
            "session_id": session_id,
            "name": candidate["name"],
            "email": candidate["email"],
            "tab_switch_count": tab_count,
            "focus_loss_count": focus_count,
            "face_absent_seconds": round(face_absent, 1),
        })

    conn.close()
    return data


def run_clustering(n_clusters=3):
    """
    Runs K-Means on all submitted sessions and returns each candidate's
    data along with a human-readable cluster label. Returns None if there
    aren't enough sessions yet to form meaningful clusters.
    """
    data = get_session_features()

    if len(data) < n_clusters:
        return None

    X = np.array([
        [d["tab_switch_count"], d["focus_loss_count"], d["face_absent_seconds"]]
        for d in data
    ])

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # Rank clusters by their centroid's total activity so labels are
    # meaningful ("Low/Moderate/High Activity") instead of arbitrary numbers.
    centroid_sums = kmeans.cluster_centers_.sum(axis=1)
    order = np.argsort(centroid_sums)

    names_by_rank = ["Low Activity", "Moderate Activity", "High Activity"]
    cluster_names = {}
    for rank, cluster_id in enumerate(order):
        cluster_names[cluster_id] = names_by_rank[rank] if rank < len(names_by_rank) else f"Cluster {cluster_id}"

    for i, d in enumerate(data):
        d["cluster_label"] = cluster_names[labels[i]]

    return data
