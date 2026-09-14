"""
Initialise the database: create all tables and seed a default admin account.

Usage (from the project root):
    python scripts/init_db.py

The default admin credentials come from .env (DEFAULT_ADMIN_USERNAME /
DEFAULT_ADMIN_PASSWORD). CHANGE THEM before any real deployment.
"""

import os
import sys

# Allow running this file directly (add project root to the import path).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from app import create_app
from extensions import db
from models.database_models import User


def main():
    app = create_app()
    with app.app_context():
        try:
            db.create_all()
        except OperationalError as exc:
            print("ERROR: Could not connect to the database.")
            print("Check that MySQL is running and your .env settings are correct.")
            print(f"Details: {exc}")
            sys.exit(1)

        tables = inspect(db.engine).get_table_names()
        print(f"Tables ready: {', '.join(tables)}")

        # Seed default admin if it does not already exist.
        username = app.config["DEFAULT_ADMIN_USERNAME"]
        password = app.config["DEFAULT_ADMIN_PASSWORD"]

        if User.query.filter_by(username=username).first():
            print(f"Admin user '{username}' already exists - skipping.")
        else:
            admin = User(username=username, role="admin")
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Created default admin '{username}'.")
            print("  -> Please change this password after first login.")

        print("Database initialisation complete.")


if __name__ == "__main__":
    main()
