"""End-to-end style tests covering validation, services, auth, API and reports."""

import pandas as pd
import pytest

from config import probability_to_category
from ml.data_validation import validate_dataframe, DataValidationError
from services.recommendation_service import get_recommendations
from services.prediction_service import run_prediction
from services.input_validation import validate_features
from tests.conftest import register, login


# --------------------------------------------------------------------------
# Data validation
# --------------------------------------------------------------------------
def _good_frame():
    return pd.DataFrame([{
        "Student_ID": 1, "Age": 22, "Gender": "Male", "Degree": "MCA",
        "Branch": "Computer Science", "CGPA": 8.2, "Internships": 2, "Projects": 4,
        "Coding_Skills": 8, "Communication_Skills": 8, "Aptitude_Test_Score": 78,
        "Soft_Skills_Rating": 8, "Certifications": 3, "Backlogs": 0,
        "Placement_Status": "Placed",
    }])


def test_validation_accepts_good_data():
    report = validate_dataframe(_good_frame())
    assert report["n_rows"] == 1
    assert report["missing_columns"] == []


def test_validation_missing_column_raises():
    df = _good_frame().drop(columns=["CGPA"])
    with pytest.raises(DataValidationError):
        validate_dataframe(df)


def test_validation_bad_label_raises():
    df = _good_frame()
    df.loc[0, "Placement_Status"] = "Maybe"
    with pytest.raises(DataValidationError):
        validate_dataframe(df)


# --------------------------------------------------------------------------
# Category mapping
# --------------------------------------------------------------------------
def test_probability_to_category():
    assert probability_to_category(0.90) == "High"
    assert probability_to_category(0.80) == "High"
    assert probability_to_category(0.65) == "Medium"
    assert probability_to_category(0.50) == "Medium"
    assert probability_to_category(0.30) == "Low"


# --------------------------------------------------------------------------
# Recommendation service
# --------------------------------------------------------------------------
def test_recommendations_for_weak_student():
    features = {
        "cgpa": 5.0, "coding_skills": 3, "communication_skills": 3,
        "aptitude_test_score": 40, "internships": 0, "projects": 0,
        "certifications": 0, "backlogs": 2,
    }
    recs = get_recommendations(features)
    assert len(recs["areas_to_improve"]) >= 6
    assert len(recs["recommended_actions"]) == len(recs["areas_to_improve"])


def test_recommendations_for_strong_student():
    features = {
        "cgpa": 9.0, "coding_skills": 9, "communication_skills": 9,
        "aptitude_test_score": 85, "internships": 2, "projects": 5,
        "certifications": 3, "backlogs": 0,
    }
    recs = get_recommendations(features)
    assert recs["areas_to_improve"] == []
    assert len(recs["strengths"]) == 8


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------
def test_input_validation_rejects_bad_cgpa():
    data = _feature_payload()
    data["cgpa"] = 15
    cleaned, errors = validate_features(data)
    assert any("cgpa" in e for e in errors)


def test_input_validation_accepts_good():
    cleaned, errors = validate_features(_feature_payload())
    assert errors == []
    assert cleaned["cgpa"] == 8.2


# --------------------------------------------------------------------------
# Prediction service (uses the injected tiny model)
# --------------------------------------------------------------------------
def test_run_prediction_shape():
    result = run_prediction(_feature_payload())
    assert result["predicted_status"] in ("Placed", "Not Placed")
    assert 0.0 <= result["probability"] <= 1.0
    assert result["category"] in ("High", "Medium", "Low")


# --------------------------------------------------------------------------
# Auth + web flow
# --------------------------------------------------------------------------
def test_register_and_login(client):
    resp = register(client)
    assert resp.status_code == 200
    resp = login(client, "stud1", "secret1")
    assert b"Logged in successfully" in resp.data


def test_student_profile_and_prediction_api(client):
    register(client)
    login(client, "stud1", "secret1")

    # Save profile.
    payload = _feature_payload()
    payload["student_id"] = "S100"
    resp = client.post("/profile", data=payload, follow_redirects=True)
    assert resp.status_code == 200

    # Predict via API (should also save a prediction).
    resp = client.post("/api/predict", json=_feature_payload())
    assert resp.status_code == 200
    data = resp.get_json()
    assert "probability_percentage" in data
    assert data["category"] in ("High", "Medium", "Low")

    # History available via API.
    resp = client.get("/api/predictions/S100")
    assert resp.status_code == 200
    assert len(resp.get_json()["predictions"]) >= 1


def test_predict_api_rejects_bad_input(client):
    register(client)
    login(client, "stud1", "secret1")
    bad = _feature_payload()
    bad["cgpa"] = 99
    resp = client.post("/api/predict", json=bad)
    assert resp.status_code == 400


def test_admin_dashboard_and_report(client, admin_user):
    login(client, "admin", "admin123")

    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200

    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    assert "total_students" in resp.get_json()

    resp = client.get("/admin/students")
    assert resp.status_code == 200

    resp = client.get("/admin/reports/download")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"


def test_student_cannot_access_admin(client):
    register(client)
    login(client, "stud1", "secret1")
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403


def test_admin_can_predict_for_any_student(client, admin_user, app):
    # Create a student profile with no prediction yet.
    from models.database_models import Student
    from extensions import db
    with app.app_context():
        s = Student(student_id="A500", **_feature_payload())
        db.session.add(s)
        db.session.commit()
        pk = s.id

    login(client, "admin", "admin123")
    resp = client.post(f"/admin/students/{pk}/predict", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        student = db.session.get(Student, pk)
        assert student.latest_prediction is not None
        assert student.latest_prediction.category in ("High", "Medium", "Low")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _feature_payload():
    return {
        "age": 22, "gender": "Male", "degree": "MCA", "branch": "CSE",
        "cgpa": 8.2, "internships": 2, "projects": 4, "coding_skills": 8,
        "communication_skills": 8, "aptitude_test_score": 78,
        "soft_skills_rating": 8, "certifications": 3, "backlogs": 0,
    }
