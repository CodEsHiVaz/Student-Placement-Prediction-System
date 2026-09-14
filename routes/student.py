"""Student-facing pages: dashboard, profile, prediction, recommendations, history."""

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash
)
from flask_login import login_required, current_user

from extensions import db
from models.database_models import Student
from routes.decorators import student_required
from services.input_validation import validate_features
from services.recommendation_service import get_recommendations
from config import (
    GENDER_OPTIONS, DEGREE_OPTIONS, BRANCH_OPTIONS,
    VALIDATION_RANGES, CATEGORY_COLORS,
)

student_bp = Blueprint("student", __name__)


def _form_context():
    """Options / ranges passed to the profile & prediction templates."""
    return {
        "gender_options": GENDER_OPTIONS,
        "degree_options": DEGREE_OPTIONS,
        "branch_options": BRANCH_OPTIONS,
        "ranges": VALIDATION_RANGES,
    }


@student_bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    student = current_user.student
    latest = student.latest_prediction if student else None
    return render_template(
        "student/dashboard.html",
        student=student,
        latest=latest,
        category_colors=CATEGORY_COLORS,
    )


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
@student_required
def profile():
    student = current_user.student

    if request.method == "POST":
        student_id = (request.form.get("student_id") or "").strip()
        cleaned, errors = validate_features(request.form)

        if not student_id:
            errors.insert(0, "Student ID is required.")
        else:
            # Enforce unique Student_ID (allow keeping your own).
            existing = Student.query.filter_by(student_id=student_id).first()
            if existing and (not student or existing.id != student.id):
                errors.insert(0, "That Student ID is already in use.")

        if errors:
            for e in errors:
                flash(e, "danger")
            # Re-render with submitted values.
            return render_template(
                "student/profile.html",
                student=_merge_form(student, request.form),
                **_form_context(),
            )

        # Create or update the linked Student profile.
        if not student:
            student = Student(user_id=current_user.id)
            db.session.add(student)
        student.student_id = student_id
        for field, value in cleaned.items():
            setattr(student, field, value)
        db.session.commit()

        flash("Profile saved successfully.", "success")
        return redirect(url_for("student.dashboard"))

    return render_template(
        "student/profile.html", student=student, **_form_context()
    )


@student_bp.route("/predict", methods=["GET"])
@login_required
@student_required
def predict_page():
    student = current_user.student
    if not student:
        flash("Please complete your profile before predicting.", "warning")
        return redirect(url_for("student.profile"))
    return render_template(
        "student/prediction.html", student=student, **_form_context()
    )


@student_bp.route("/recommendations")
@login_required
@student_required
def recommendations():
    student = current_user.student
    if not student:
        flash("Please complete your profile first.", "warning")
        return redirect(url_for("student.profile"))
    recs = get_recommendations(student.to_feature_dict())
    return render_template(
        "student/recommendations.html", student=student, recs=recs
    )


@student_bp.route("/history")
@login_required
@student_required
def history():
    student = current_user.student
    predictions = student.predictions if student else []
    return render_template(
        "student/history.html",
        student=student,
        predictions=predictions,
        category_colors=CATEGORY_COLORS,
    )


def _merge_form(student, form):
    """Build a lightweight object of submitted values to refill the form."""
    class _Obj:
        pass

    obj = _Obj()
    obj.student_id = form.get("student_id", getattr(student, "student_id", "") or "")
    fields = ["age", "gender", "degree", "branch", "cgpa", "internships",
              "projects", "coding_skills", "communication_skills",
              "aptitude_test_score", "soft_skills_rating", "certifications",
              "backlogs"]
    for f in fields:
        setattr(obj, f, form.get(f, getattr(student, f, "") if student else ""))
    return obj
