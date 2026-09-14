"""Admin / placement-officer pages: dashboard, student management, reports."""

import csv
import io

from flask import (
    Blueprint, render_template, request, Response, abort, redirect, url_for, flash
)
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models.database_models import Student, Prediction
from routes.decorators import admin_required
from services import stats_service
from services.prediction_service import predict_and_save
from config import Config, DEGREE_OPTIONS, BRANCH_OPTIONS, CATEGORY_COLORS
from ml.predict import load_metadata, ModelNotAvailable

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    stats = stats_service.dashboard_stats()
    metadata = load_metadata()  # latest model performance (may be {})
    return render_template("admin/dashboard.html", stats=stats, metadata=metadata)


def _filtered_students_query():
    """Build a Student query from the request's search/filter args."""
    search = (request.args.get("search") or "").strip()
    degree = (request.args.get("degree") or "").strip()
    branch = (request.args.get("branch") or "").strip()
    category = (request.args.get("category") or "").strip()

    query = Student.query
    if search:
        query = query.filter(Student.student_id.like(f"%{search}%"))
    if degree:
        query = query.filter(Student.degree == degree)
    if branch:
        query = query.filter(Student.branch == branch)

    if category:
        # Filter by the category of each student's latest prediction.
        latest = (
            db.session.query(
                Prediction.student_id.label("sid"),
                func.max(Prediction.id).label("mid"),
            )
            .group_by(Prediction.student_id)
            .subquery()
        )
        query = (
            query.join(latest, latest.c.sid == Student.id)
            .join(Prediction, Prediction.id == latest.c.mid)
            .filter(Prediction.category == category)
        )

    return query.order_by(Student.id)


@admin_bp.route("/students")
@login_required
@admin_required
def students():
    page = request.args.get("page", 1, type=int)
    pagination = _filtered_students_query().paginate(
        page=page, per_page=Config.STUDENTS_PER_PAGE, error_out=False
    )
    return render_template(
        "admin/students.html",
        pagination=pagination,
        students=pagination.items,
        degree_options=DEGREE_OPTIONS,
        branch_options=BRANCH_OPTIONS,
        category_colors=CATEGORY_COLORS,
        filters={
            "search": request.args.get("search", ""),
            "degree": request.args.get("degree", ""),
            "branch": request.args.get("branch", ""),
            "category": request.args.get("category", ""),
        },
    )


@admin_bp.route("/students/<int:student_pk>")
@login_required
@admin_required
def student_detail(student_pk):
    student = db.session.get(Student, student_pk)
    if not student:
        abort(404)
    return render_template(
        "admin/student_detail.html",
        student=student,
        predictions=student.predictions,
        category_colors=CATEGORY_COLORS,
    )


@admin_bp.route("/students/<int:student_pk>/predict", methods=["POST"])
@login_required
@admin_required
def predict_student(student_pk):
    """Run (and save) a placement prediction for any student."""
    student = db.session.get(Student, student_pk)
    if not student:
        abort(404)

    try:
        result = predict_and_save(student)
        flash(
            f"Prediction for {student.student_id}: {result['predicted_status']} "
            f"({result['probability_percentage']}% - {result['category']}).",
            "success",
        )
    except ModelNotAvailable:
        flash("Model not available. Train it first: python ml/train_model.py", "danger")

    # Return to wherever the admin triggered the prediction from.
    # Only allow local (relative) paths to avoid open-redirects.
    next_url = request.form.get("next", "")
    if not next_url.startswith("/"):
        next_url = url_for("admin.student_detail", student_pk=student.id)
    return redirect(next_url)


@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    total_predictions = db.session.query(func.count(Prediction.id)).scalar() or 0
    return render_template("admin/reports.html", total_predictions=total_predictions)


@admin_bp.route("/reports/download")
@login_required
@admin_required
def download_report():
    """Generate a CSV report from each student's latest prediction."""
    # Latest prediction per student.
    latest = (
        db.session.query(
            Prediction.student_id.label("sid"),
            func.max(Prediction.id).label("mid"),
        )
        .group_by(Prediction.student_id)
        .subquery()
    )
    rows = (
        db.session.query(Student, Prediction)
        .join(latest, latest.c.sid == Student.id)
        .join(Prediction, Prediction.id == latest.c.mid)
        .order_by(Student.student_id)
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Student_ID", "Degree", "Branch", "CGPA", "Aptitude_Test_Score",
        "Coding_Skills", "Communication_Skills", "Predicted_Status",
        "Probability", "Category",
    ])
    for student, pred in rows:
        writer.writerow([
            student.student_id, student.degree, student.branch, student.cgpa,
            student.aptitude_test_score, student.coding_skills,
            student.communication_skills, pred.predicted_status,
            round(pred.probability, 4), pred.category,
        ])

    output = buffer.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=placement_report.csv"},
    )
