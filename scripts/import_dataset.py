"""
Import student records from data/student_placement.csv into MySQL.

Usage (from the project root):
    python scripts/import_dataset.py

- Validates the CSV columns.
- Cleans values.
- Skips Student_IDs that already exist in the database.
- Uses efficient bulk inserts (in chunks), not one INSERT per row.
- Prints progress and a final inserted / skipped summary.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from sqlalchemy.exc import OperationalError

from app import create_app
from config import Config
from extensions import db
from models.database_models import Student
from ml.data_validation import validate_dataframe, print_report, DataValidationError

CHUNK_SIZE = 1000

# Map CSV column -> Student model attribute.
COLUMN_MAP = {
    "Age": "age",
    "Gender": "gender",
    "Degree": "degree",
    "Branch": "branch",
    "CGPA": "cgpa",
    "Internships": "internships",
    "Projects": "projects",
    "Coding_Skills": "coding_skills",
    "Communication_Skills": "communication_skills",
    "Aptitude_Test_Score": "aptitude_test_score",
    "Soft_Skills_Rating": "soft_skills_rating",
    "Certifications": "certifications",
    "Backlogs": "backlogs",
}
INT_ATTRS = {
    "age", "internships", "projects", "coding_skills", "communication_skills",
    "aptitude_test_score", "soft_skills_rating", "certifications", "backlogs",
}


def _to_int(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_student(row):
    """Create a Student object from a CSV row (pandas Series)."""
    kwargs = {"student_id": str(row["Student_ID"]).strip()}
    for csv_col, attr in COLUMN_MAP.items():
        value = row.get(csv_col)
        if attr == "cgpa":
            kwargs[attr] = _to_float(value)
        elif attr in INT_ATTRS:
            kwargs[attr] = _to_int(value)
        else:  # gender / degree / branch
            kwargs[attr] = None if pd.isna(value) else str(value).strip()
    return Student(**kwargs)


def main():
    path = Config.DATASET_PATH
    if not os.path.exists(path):
        print(f"ERROR: Dataset not found at '{path}'.")
        print("Place your CSV at data/student_placement.csv and try again.")
        sys.exit(1)

    print(f"Reading dataset: {path}")
    df = pd.read_csv(path)

    try:
        report = validate_dataframe(df, strict_labels=False)
    except DataValidationError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    print_report(report)

    # Drop rows with a missing / duplicate Student_ID inside the file itself.
    df = df.dropna(subset=["Student_ID"])
    df = df.drop_duplicates(subset=["Student_ID"], keep="first")

    app = create_app()
    with app.app_context():
        try:
            existing_ids = {sid for (sid,) in db.session.query(Student.student_id).all()}
        except OperationalError as exc:
            print("ERROR: Could not connect to the database.")
            print("Make sure MySQL is running, the database exists, and .env is correct.")
            print("Also run: python scripts/init_db.py")
            print(f"Details: {exc}")
            sys.exit(1)

        total = len(df)
        inserted = 0
        skipped = 0
        batch = []

        for i, (_, row) in enumerate(df.iterrows(), start=1):
            sid = str(row["Student_ID"]).strip()
            if sid in existing_ids:
                skipped += 1
                continue
            existing_ids.add(sid)
            batch.append(build_student(row))

            if len(batch) >= CHUNK_SIZE:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                inserted += len(batch)
                batch = []
                print(f"  Progress: {i}/{total} rows processed, {inserted} inserted...")

        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            inserted += len(batch)

        print("-" * 50)
        print(f"Import complete. Inserted: {inserted}   Skipped (duplicates): {skipped}")
        print(f"Total students in database: {Student.query.count()}")


if __name__ == "__main__":
    main()
