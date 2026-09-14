"""
SQLAlchemy database models: User, Student and Prediction.

Passwords are stored only as Werkzeug hashes, never as plain text.
"""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    """Login account. Role is either 'student' or 'admin'."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # A user may have one linked student profile (for role == student).
    student = db.relationship("Student", back_populates="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Student(db.Model):
    """A student profile holding the features used for prediction."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    # Linked login account (nullable: dataset-imported students have no login).
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    degree = db.Column(db.String(50))
    branch = db.Column(db.String(50))
    cgpa = db.Column(db.Float)
    internships = db.Column(db.Integer, default=0)
    projects = db.Column(db.Integer, default=0)
    coding_skills = db.Column(db.Integer, default=0)
    communication_skills = db.Column(db.Integer, default=0)
    aptitude_test_score = db.Column(db.Integer, default=0)
    soft_skills_rating = db.Column(db.Integer, default=0)
    certifications = db.Column(db.Integer, default=0)
    backlogs = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship("User", back_populates="student")
    predictions = db.relationship(
        "Prediction",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="Prediction.created_at.desc()",
    )

    def to_feature_dict(self):
        """Return the feature values as the dict the ML pipeline expects."""
        return {
            "age": self.age,
            "gender": self.gender,
            "degree": self.degree,
            "branch": self.branch,
            "cgpa": self.cgpa,
            "internships": self.internships,
            "projects": self.projects,
            "coding_skills": self.coding_skills,
            "communication_skills": self.communication_skills,
            "aptitude_test_score": self.aptitude_test_score,
            "soft_skills_rating": self.soft_skills_rating,
            "certifications": self.certifications,
            "backlogs": self.backlogs,
        }

    @property
    def latest_prediction(self):
        return self.predictions[0] if self.predictions else None

    def __repr__(self):
        return f"<Student {self.student_id}>"


class Prediction(db.Model):
    """A single stored prediction result for a student."""

    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    predicted_status = db.Column(db.String(20), nullable=False)  # Placed / Not Placed
    probability = db.Column(db.Float, nullable=False)            # 0.0 - 1.0
    category = db.Column(db.String(10), nullable=False)          # High/Medium/Low
    model_version = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("Student", back_populates="predictions")

    @property
    def probability_percentage(self):
        return round(self.probability * 100, 1)

    def __repr__(self):
        return f"<Prediction {self.predicted_status} {self.probability:.2f}>"
