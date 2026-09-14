"""
Dataset validation shared by training and import.

The goal is to catch data problems early and clearly, instead of silently
training a bad model. validate_dataframe() returns a report dict and raises
ValueError on fatal problems (missing columns, bad placement labels).
"""

import pandas as pd

from config import (
    REQUIRED_COLUMNS,
    NUMERIC_FEATURES,
    ID_COL,
    TARGET,
    VALID_PLACEMENT_LABELS,
    VALIDATION_RANGES,
)


class DataValidationError(ValueError):
    """Raised when the dataset has a fatal problem that must stop processing."""


def validate_dataframe(df, strict_labels=True):
    """Validate a student dataframe.

    Returns a report dict. Raises DataValidationError for fatal issues:
      - missing required columns
      - unexpected Placement_Status labels (when strict_labels=True)
    """
    report = {
        "n_rows": len(df),
        "n_cols": df.shape[1],
        "missing_columns": [],
        "missing_values": {},
        "duplicate_student_ids": 0,
        "out_of_range": {},
        "negative_counts": {},
        "unexpected_labels": [],
    }

    # 1. Required columns must all be present.
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    report["missing_columns"] = missing_cols
    if missing_cols:
        raise DataValidationError(
            "Dataset is missing required columns: " + ", ".join(missing_cols)
        )

    # 2. Missing values per column (informational).
    na_counts = df.isna().sum()
    report["missing_values"] = {c: int(n) for c, n in na_counts.items() if n > 0}

    # 3. Duplicate Student_ID.
    report["duplicate_student_ids"] = int(df[ID_COL].duplicated().sum())

    # 4. Numeric range checks (map dataframe column -> config key).
    col_to_range_key = {
        "Age": "age",
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
    for col, key in col_to_range_key.items():
        if col not in df.columns:
            continue
        lo, hi = VALIDATION_RANGES[key]
        numeric = pd.to_numeric(df[col], errors="coerce")
        bad = int(((numeric < lo) | (numeric > hi)).sum())
        if bad:
            report["out_of_range"][col] = bad

    # 5. Negative counts (should never be negative).
    for col in ["Internships", "Projects", "Certifications", "Backlogs"]:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            neg = int((numeric < 0).sum())
            if neg:
                report["negative_counts"][col] = neg

    # 6. Placement_Status labels.
    labels = set(df[TARGET].dropna().unique())
    unexpected = labels - VALID_PLACEMENT_LABELS
    report["unexpected_labels"] = sorted(str(x) for x in unexpected)
    if strict_labels and unexpected:
        raise DataValidationError(
            f"Unexpected {TARGET} labels found: {report['unexpected_labels']}. "
            f"Only {sorted(VALID_PLACEMENT_LABELS)} are allowed."
        )

    return report


def print_report(report):
    """Print a human-readable validation report."""
    print("=" * 60)
    print("DATA VALIDATION REPORT")
    print("=" * 60)
    print(f"Rows: {report['n_rows']}   Columns: {report['n_cols']}")

    print(f"Duplicate {ID_COL}: {report['duplicate_student_ids']}")

    if report["missing_values"]:
        print("\nMissing values:")
        for col, n in report["missing_values"].items():
            print(f"  - {col}: {n}")
    else:
        print("Missing values: none")

    if report["out_of_range"]:
        print("\nOut-of-range values:")
        for col, n in report["out_of_range"].items():
            print(f"  - {col}: {n}")

    if report["negative_counts"]:
        print("\nNegative counts:")
        for col, n in report["negative_counts"].items():
            print(f"  - {col}: {n}")

    if report["unexpected_labels"]:
        print(f"\nUnexpected placement labels: {report['unexpected_labels']}")

    print("=" * 60)
