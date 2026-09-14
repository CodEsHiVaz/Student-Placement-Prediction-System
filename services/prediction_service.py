"""
Prediction business logic.

Keeps the routes thin: they pass a plain feature dict here, and this module
handles the ML call, the High/Medium/Low mapping and (optionally) saving the
result to the database.
"""

from extensions import db
from models.database_models import Prediction
from ml.predict import predict_one, get_model_version
from config import probability_to_category


def run_prediction(features):
    """Run the model on a feature dict and return a result dict.

    Returns:
        {
          "predicted_status": "Placed" | "Not Placed",
          "probability": 0.87,               # 0..1
          "probability_percentage": 87.0,    # 0..100
          "category": "High" | "Medium" | "Low"
        }
    """
    status, probability = predict_one(features)
    return {
        "predicted_status": status,
        "probability": round(probability, 4),
        "probability_percentage": round(probability * 100, 1),
        "category": probability_to_category(probability),
    }


def save_prediction(student, result):
    """Persist a prediction result for a given Student row."""
    prediction = Prediction(
        student_id=student.id,
        predicted_status=result["predicted_status"],
        probability=result["probability"],
        category=result["category"],
        model_version=get_model_version(),
    )
    db.session.add(prediction)
    db.session.commit()
    return prediction


def predict_and_save(student):
    """Convenience: run a prediction for a Student and store it."""
    result = run_prediction(student.to_feature_dict())
    save_prediction(student, result)
    return result
