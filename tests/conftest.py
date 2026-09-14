"""
Pytest fixtures.

Tests use an in-memory SQLite database (TestConfig) so they never touch MySQL,
and a tiny model trained in-memory so they never need the real 45k dataset or a
saved .pkl file.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

from config import TestConfig, ALL_FEATURES
from app import create_app
from extensions import db as _db
import ml.predict as predict_mod
from ml.train_model import build_preprocessor


def _tiny_training_frame():
    """A small, clearly-separable dataset so the model trains sensibly."""
    strong = {
        "Age": 22, "Gender": "Male", "Degree": "MCA", "Branch": "Computer Science",
        "CGPA": 8.5, "Internships": 2, "Projects": 4, "Coding_Skills": 8,
        "Communication_Skills": 8, "Aptitude_Test_Score": 80,
        "Soft_Skills_Rating": 8, "Certifications": 3, "Backlogs": 0,
    }
    weak = {
        "Age": 23, "Gender": "Female", "Degree": "BCA", "Branch": "IT",
        "CGPA": 5.0, "Internships": 0, "Projects": 0, "Coding_Skills": 3,
        "Communication_Skills": 3, "Aptitude_Test_Score": 40,
        "Soft_Skills_Rating": 3, "Certifications": 0, "Backlogs": 3,
    }
    rows, labels = [], []
    for _ in range(30):
        rows.append(strong); labels.append(1)
        rows.append(weak); labels.append(0)
    return pd.DataFrame(rows), pd.Series(labels)


@pytest.fixture(scope="session", autouse=True)
def _inject_model():
    """Train a tiny pipeline once and inject it into ml.predict's cache."""
    X, y = _tiny_training_frame()
    pipe = Pipeline(steps=[
        ("preprocessor", build_preprocessor()),
        ("model", LogisticRegression(max_iter=1000)),
    ])
    pipe.fit(X[ALL_FEATURES], y)
    predict_mod._model = pipe
    predict_mod._metadata = {"model_version": "test-model"}
    yield


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    from models.database_models import User
    user = User(username="admin", role="admin")
    user.set_password("admin123")
    _db.session.add(user)
    _db.session.commit()
    return user


def register(client, username="stud1", password="secret1"):
    return client.post("/register", data={
        "username": username, "password": password, "confirm_password": password,
    }, follow_redirects=True)


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)
