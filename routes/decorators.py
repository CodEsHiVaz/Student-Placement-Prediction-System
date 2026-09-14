"""Small reusable decorators for role-based access control."""

from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(view):
    """Allow only logged-in admins; otherwise return 403."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def student_required(view):
    """Allow only logged-in students; otherwise return 403."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
