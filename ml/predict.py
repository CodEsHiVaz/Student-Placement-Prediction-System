"""
Model inference.

Loads the trained joblib pipeline once (cached at module level) and exposes
predict_one() for a single student. All preprocessing lives inside the saved
pipeline, so this module only builds a one-row DataFrame and calls it.

Input feature keys are lowercase (e.g. "coding_skills"); they map to the
dataset column names by simple title-casing (Coding_Skills), because for every
feature column, column.lower() == input key.
"""

import os
import json

import pandas as pd
import joblib

from config import Config, ALL_FEATURES

# Module-level caches so the model is loaded only once.
_model = None
_metadata = None


class ModelNotAvailable(RuntimeError):
    """Raised when the trained model file is missing."""


def load_model():
    """Load and cache the trained pipeline."""
    global _model
    if _model is None:
        path = Config.MODEL_PATH
        if not os.path.exists(path):
            raise ModelNotAvailable(
                f"Trained model not found at '{path}'. "
                "Run: python ml/train_model.py"
            )
        _model = joblib.load(path)
    return _model


def load_metadata():
    """Load and cache model metadata (returns {} if not present)."""
    global _metadata
    if _metadata is None:
        path = Config.MODEL_METADATA_PATH
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _metadata = json.load(f)
        else:
            _metadata = {}
    return _metadata


def get_model_version():
    return load_metadata().get("model_version", "unknown")


def predict_one(features):
    """Predict placement for a single student.

    Args:
        features: dict with lowercase keys (age, gender, degree, branch, cgpa,
        internships, projects, coding_skills, communication_skills,
        aptitude_test_score, soft_skills_rating, certifications, backlogs).

    Returns:
        (predicted_status: str, probability: float in 0..1)
    """
    model = load_model()

    # Build a one-row DataFrame with the exact column names the pipeline expects.
    row = {col: features.get(col.lower()) for col in ALL_FEATURES}
    X = pd.DataFrame([row], columns=ALL_FEATURES)

    pred = int(model.predict(X)[0])
    proba = float(model.predict_proba(X)[0][1])  # probability of class 1 (Placed)

    status = "Placed" if pred == 1 else "Not Placed"
    return status, proba
