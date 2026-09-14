"""
Server-side validation of student feature input.

Used by both the JSON prediction API and the profile form so the rules live in
one place (backed by config.VALIDATION_RANGES). Never trust the client.
"""

from config import (
    VALIDATION_RANGES,
    GENDER_OPTIONS,
    DEGREE_OPTIONS,
    BRANCH_OPTIONS,
)

NUMERIC_FIELDS = list(VALIDATION_RANGES.keys())
INT_FIELDS = {
    "age", "internships", "projects", "coding_skills", "communication_skills",
    "aptitude_test_score", "soft_skills_rating", "certifications", "backlogs",
}
CATEGORICAL_FIELDS = {
    "gender": GENDER_OPTIONS,
    "degree": DEGREE_OPTIONS,
    "branch": BRANCH_OPTIONS,
}


def validate_features(data):
    """Validate and clean a raw input dict.

    Args:
        data: dict-like mapping (from JSON or a form) with the student fields.

    Returns:
        (cleaned: dict, errors: list[str])
        cleaned holds properly typed values; only trustworthy if errors is empty.
    """
    cleaned = {}
    errors = []

    # Numeric fields.
    for field in NUMERIC_FIELDS:
        raw = data.get(field)
        if raw is None or raw == "":
            errors.append(f"{field} is required.")
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            errors.append(f"{field} must be a number.")
            continue

        lo, hi = VALIDATION_RANGES[field]
        if value < lo or value > hi:
            errors.append(f"{field} must be between {lo} and {hi}.")
            continue

        cleaned[field] = int(round(value)) if field in INT_FIELDS else value

    # Categorical fields.
    for field, options in CATEGORICAL_FIELDS.items():
        raw = data.get(field)
        if raw is None or str(raw).strip() == "":
            errors.append(f"{field} is required.")
            continue
        value = str(raw).strip()
        if value not in options:
            errors.append(f"{field} must be one of: {', '.join(options)}.")
            continue
        cleaned[field] = value

    return cleaned, errors
