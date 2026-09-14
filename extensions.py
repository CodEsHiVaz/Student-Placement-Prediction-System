"""
Shared Flask extension instances.

They are created here (without an app) and initialised later in create_app()
via init_app(). This avoids circular imports between app.py, models and routes.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
