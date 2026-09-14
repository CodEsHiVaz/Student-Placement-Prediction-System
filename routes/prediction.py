"""
JSON API endpoints (kept thin; business logic lives in services/).

    POST /api/predict
    GET  /api/predictions/<student_id>
    GET  /api/dashboard/stats
    GET  /api/students
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.database_models import Student, Prediction
from services.input_validation import validate_features
from services.prediction_service import run_prediction
from services import stats_service
from ml.predict import ModelNotAvailable

prediction_bp = Blueprint("prediction", __name__, url_prefix="/api")


@prediction_bp.route("/predict", methods=["POST"])
@login_required
def api_predict():
    """Predict placement for the posted feature JSON."""
    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_features(data)
    if errors:
        return jsonify(error="Invalid input", details=errors), 400

    try:
        result = run_prediction(cleaned)
    except ModelNotAvailable as exc:
        return jsonify(error=str(exc)), 503

    # If this is a student with a saved profile, persist the prediction.
    if not current_user.is_admin and current_user.student:
        from services.prediction_service import save_prediction
        save_prediction(current_user.student, result)

    return jsonify(result)


@prediction_bp.route("/predictions/<student_id>", methods=["GET"])
@login_required
def api_predictions(student_id):
    """Prediction history for a student (by Student_ID string)."""
    student = Student.query.filter_by(student_id=str(student_id)).first()
    if not student:
        return jsonify(error="Student not found"), 404

    # A student may only see their own history.
    if not current_user.is_admin and student.user_id != current_user.id:
        return jsonify(error="Forbidden"), 403

    history = [
        {
            "predicted_status": p.predicted_status,
            "probability": p.probability,
            "probability_percentage": p.probability_percentage,
            "category": p.category,
            "model_version": p.model_version,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in student.predictions
    ]
    return jsonify(student_id=student.student_id, predictions=history)


@prediction_bp.route("/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    """Aggregate statistics for the admin dashboard charts."""
    if not current_user.is_admin:
        return jsonify(error="Forbidden"), 403
    return jsonify(stats_service.dashboard_stats())


@prediction_bp.route("/students", methods=["GET"])
@login_required
def api_students():
    """Paginated student list (admin only)."""
    if not current_user.is_admin:
        return jsonify(error="Forbidden"), 403

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = Student.query.order_by(Student.id).paginate(
        page=page, per_page=per_page, error_out=False
    )
    students = [
        {
            "student_id": s.student_id,
            "degree": s.degree,
            "branch": s.branch,
            "cgpa": s.cgpa,
        }
        for s in pagination.items
    ]
    return jsonify(
        students=students,
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
    )
