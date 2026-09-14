"""
Aggregate statistics for the admin dashboard.

All numbers come from the database (students + predictions tables), never
hard-coded. Kept separate from routes so it can be reused/extended later.
"""

from sqlalchemy import func

from extensions import db
from models.database_models import Student, Prediction


def dashboard_stats():
    """Return a dict of all figures the admin dashboard needs."""
    total_students = db.session.query(func.count(Student.id)).scalar() or 0
    total_predictions = db.session.query(func.count(Prediction.id)).scalar() or 0

    # Placed vs Not Placed (over all stored predictions).
    status_counts = dict(
        db.session.query(Prediction.predicted_status, func.count(Prediction.id))
        .group_by(Prediction.predicted_status)
        .all()
    )
    predicted_placed = status_counts.get("Placed", 0)
    predicted_not_placed = status_counts.get("Not Placed", 0)

    # High / Medium / Low.
    category_counts = dict(
        db.session.query(Prediction.category, func.count(Prediction.id))
        .group_by(Prediction.category)
        .all()
    )
    high = category_counts.get("High", 0)
    medium = category_counts.get("Medium", 0)
    low = category_counts.get("Low", 0)

    # Branch-wise student distribution.
    branch_rows = (
        db.session.query(Student.branch, func.count(Student.id))
        .group_by(Student.branch)
        .order_by(func.count(Student.id).desc())
        .all()
    )
    branch_distribution = {(b or "Unknown"): n for b, n in branch_rows}

    return {
        "total_students": total_students,
        "total_predictions": total_predictions,
        "predicted_placed": predicted_placed,
        "predicted_not_placed": predicted_not_placed,
        "high": high,
        "medium": medium,
        "low": low,
        "branch_distribution": branch_distribution,
        "cgpa_vs_placement": _cgpa_vs_placement(),
    }


def _cgpa_vs_placement():
    """CGPA buckets vs predicted placed / not placed (from predictions)."""
    bins = [(0, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10.01)]
    labels = ["<5", "5-6", "6-7", "7-8", "8-9", "9-10"]
    placed = [0] * len(bins)
    not_placed = [0] * len(bins)

    rows = (
        db.session.query(Student.cgpa, Prediction.predicted_status)
        .join(Prediction, Prediction.student_id == Student.id)
        .all()
    )
    for cgpa, status in rows:
        if cgpa is None:
            continue
        for i, (lo, hi) in enumerate(bins):
            if lo <= cgpa < hi:
                if status == "Placed":
                    placed[i] += 1
                else:
                    not_placed[i] += 1
                break

    return {"labels": labels, "placed": placed, "not_placed": not_placed}
