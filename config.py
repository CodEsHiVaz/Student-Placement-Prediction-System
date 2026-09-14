"""
Central configuration for the Student Placement Prediction System.

Everything that a developer might want to tune later lives here:
  - environment / database settings
  - probability thresholds (High / Medium / Low)
  - which columns are features (and their types)
  - input validation ranges
  - recommendation rules

Keeping these in one place means new features can be added later without
hunting through the whole codebase.
"""

import os
from dotenv import load_dotenv

# Load variables from a local .env file if present.
load_dotenv()

# Project root directory (folder containing this file).
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _abs(path):
    """Turn a project-relative path into an absolute path."""
    if os.path.isabs(path):
        return path
    return os.path.join(BASE_DIR, path)


class Config:
    """Base configuration read from environment variables."""

    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    # --- MySQL / SQLAlchemy ---
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "student_placement")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Machine learning ---
    MODEL_PATH = _abs(os.getenv("MODEL_PATH", "ml/models/placement_model.pkl"))
    MODEL_METADATA_PATH = _abs("ml/models/model_metadata.json")
    # Dataset location; can be overridden with DATASET_PATH in .env.
    DATASET_PATH = _abs(os.getenv("DATASET_PATH", "data/student_placement.csv"))

    # --- Default admin (seeded by scripts/init_db.py) ---
    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

    # --- Logging ---
    LOG_DIR = _abs("logs")
    LOG_FILE = _abs("logs/app.log")

    # --- Pagination ---
    STUDENTS_PER_PAGE = 20


class TestConfig(Config):
    """Configuration used only by the automated tests.

    Uses an in-memory SQLite database so tests never touch MySQL.
    """

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret"


# ---------------------------------------------------------------------------
# Dataset / ML column definitions
# ---------------------------------------------------------------------------

# Identifier column - NOT used as an ML feature.
ID_COL = "Student_ID"

# Target column and the label mapping used for training.
TARGET = "Placement_Status"
TARGET_MAP = {"Placed": 1, "Not Placed": 0}
VALID_PLACEMENT_LABELS = set(TARGET_MAP.keys())

# Features grouped by type (used to build the preprocessing ColumnTransformer).
CATEGORICAL_FEATURES = ["Gender", "Degree", "Branch"]
NUMERIC_FEATURES = [
    "Age",
    "CGPA",
    "Internships",
    "Projects",
    "Coding_Skills",
    "Communication_Skills",
    "Aptitude_Test_Score",
    "Soft_Skills_Rating",
    "Certifications",
    "Backlogs",
]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Every column the dataset is expected to contain.
REQUIRED_COLUMNS = [ID_COL] + ALL_FEATURES + [TARGET]


# ---------------------------------------------------------------------------
# Probability -> category thresholds (easily changeable)
# ---------------------------------------------------------------------------
# 80% and above  = High
# 50% to 79.99%  = Medium
# below 50%      = Low
PROBABILITY_THRESHOLDS = {"high": 0.80, "medium": 0.50}


def probability_to_category(probability):
    """Convert a placement probability (0.0-1.0) into High / Medium / Low."""
    if probability >= PROBABILITY_THRESHOLDS["high"]:
        return "High"
    if probability >= PROBABILITY_THRESHOLDS["medium"]:
        return "Medium"
    return "Low"


# Bootstrap colour class per category (used in templates).
CATEGORY_COLORS = {"High": "success", "Medium": "warning", "Low": "danger"}


# ---------------------------------------------------------------------------
# Input validation ranges (form validation lives here so it is easy to change)
# ---------------------------------------------------------------------------
# Each entry: field -> (min, max). Counts use a large upper bound.
VALIDATION_RANGES = {
    "age": (15, 60),
    "cgpa": (0, 10),
    "internships": (0, 50),
    "projects": (0, 100),
    "coding_skills": (0, 10),
    "communication_skills": (0, 10),
    "aptitude_test_score": (0, 100),
    "soft_skills_rating": (0, 10),
    "certifications": (0, 100),
    "backlogs": (0, 50),
}

# Allowed values for the categorical dropdowns in the prediction form.
# These match the categories present in the dataset so the model always
# receives values it was trained on.
GENDER_OPTIONS = ["Male", "Female"]
DEGREE_OPTIONS = ["B.Tech", "BCA", "MCA", "B.Sc"]
BRANCH_OPTIONS = ["CSE", "IT", "ECE", "ME", "Civil"]


# ---------------------------------------------------------------------------
# Recommendation rules (rule-based engine, no ML)
# ---------------------------------------------------------------------------
# Each rule compares a student field against a threshold.
#   operator "<"  -> weak when value < threshold
#   operator "==" -> weak when value == threshold
#   operator ">"  -> weak when value > threshold
# When the rule is NOT triggered, the student gets a "strength" message.
RECOMMENDATION_RULES = [
    {
        "field": "cgpa",
        "operator": "<",
        "threshold": 7,
        "improve": "CGPA is below 7 - academic performance can be improved.",
        "action": "Focus on core subjects and aim to raise your CGPA above 7.",
        "strength": "Strong academic performance (CGPA 7 or above).",
    },
    {
        "field": "coding_skills",
        "operator": "<",
        "threshold": 6,
        "improve": "Coding skills are below average.",
        "action": "Practice programming and Data Structures & Algorithms regularly.",
        "strength": "Good coding skills.",
    },
    {
        "field": "communication_skills",
        "operator": "<",
        "threshold": 6,
        "improve": "Communication skills need improvement.",
        "action": "Practice communication, group discussions and mock interviews.",
        "strength": "Good communication skills.",
    },
    {
        "field": "aptitude_test_score",
        "operator": "<",
        "threshold": 60,
        "improve": "Aptitude test score is low.",
        "action": "Prepare for aptitude tests (quant, logical reasoning, verbal).",
        "strength": "Strong aptitude test score.",
    },
    {
        "field": "internships",
        "operator": "==",
        "threshold": 0,
        "improve": "No internship experience.",
        "action": "Apply for internships to gain practical industry experience.",
        "strength": "Has internship experience.",
    },
    {
        "field": "projects",
        "operator": "<",
        "threshold": 2,
        "improve": "Few practical projects.",
        "action": "Build more hands-on projects to strengthen your portfolio.",
        "strength": "Has a good number of projects.",
    },
    {
        "field": "certifications",
        "operator": "==",
        "threshold": 0,
        "improve": "No certifications.",
        "action": "Earn relevant certifications in your field of interest.",
        "strength": "Has relevant certifications.",
    },
    {
        "field": "backlogs",
        "operator": ">",
        "threshold": 0,
        "improve": "You currently have backlogs.",
        "action": "Clear pending backlogs as soon as possible.",
        "strength": "No pending backlogs.",
    },
]
