"""
Application entry point.

Uses the "application factory" pattern (create_app) so the app is easy to
configure, test and extend later. Run locally with:  python app.py
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request, jsonify

from config import Config
from extensions import db, login_manager, csrf


def create_app(config_object=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Initialise extensions.
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    _configure_logging(app)
    _register_user_loader()
    _register_blueprints(app)
    _register_error_handlers(app)

    return app


def _configure_logging(app):
    """Log warnings and errors to a rotating file (never to the user)."""
    os.makedirs(app.config["LOG_DIR"], exist_ok=True)
    handler = RotatingFileHandler(
        app.config["LOG_FILE"], maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]")
    )
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def _register_user_loader():
    """Tell Flask-Login how to load a user from the session."""
    from models.database_models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


def _register_blueprints(app):
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.admin import admin_bp
    from routes.prediction import prediction_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(prediction_bp)

    # The JSON API uses tokens/JSON, not HTML forms, so exempt it from CSRF.
    csrf.exempt(prediction_bp)


def _register_error_handlers(app):
    """Show friendly pages instead of Python stack traces."""

    def wants_json():
        return request.path.startswith("/api/")

    @app.errorhandler(404)
    def not_found(e):
        if wants_json():
            return jsonify(error="Not found"), 404
        return render_template("error.html", code=404,
                               message="Page not found."), 404

    @app.errorhandler(403)
    def forbidden(e):
        if wants_json():
            return jsonify(error="Forbidden"), 403
        return render_template("error.html", code=403,
                               message="You do not have permission to view this page."), 403

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal server error")
        if wants_json():
            return jsonify(error="Internal server error"), 500
        return render_template("error.html", code=500,
                               message="Something went wrong. Please try again later."), 500


if __name__ == "__main__":
    # `python app.py` runs the app. For `flask run`, use:  flask --app app run
    # (Flask auto-detects the create_app factory.)
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
