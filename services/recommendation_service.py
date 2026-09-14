"""
Rule-based recommendation engine (no ML).

Reads the rules from config.RECOMMENDATION_RULES and produces the student's
strengths, areas to improve and recommended actions from their actual data.
"""

from config import RECOMMENDATION_RULES


def _is_weak(value, operator, threshold):
    """Return True if the value triggers the 'weak' condition."""
    if value is None:
        return False
    if operator == "<":
        return value < threshold
    if operator == ">":
        return value > threshold
    if operator == "==":
        return value == threshold
    return False


def get_recommendations(features):
    """Analyse a feature dict and return strengths / improvements / actions.

    Args:
        features: dict with lowercase keys matching the rule "field" values
                  (cgpa, coding_skills, communication_skills, ...).

    Returns:
        {"strengths": [...], "areas_to_improve": [...], "recommended_actions": [...]}
    """
    strengths = []
    areas_to_improve = []
    recommended_actions = []

    for rule in RECOMMENDATION_RULES:
        value = features.get(rule["field"])
        if _is_weak(value, rule["operator"], rule["threshold"]):
            areas_to_improve.append(rule["improve"])
            recommended_actions.append(rule["action"])
        else:
            strengths.append(rule["strength"])

    return {
        "strengths": strengths,
        "areas_to_improve": areas_to_improve,
        "recommended_actions": recommended_actions,
    }
