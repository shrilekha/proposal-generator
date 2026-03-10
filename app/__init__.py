import os

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import get_config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    # Ensure generated_files directory exists
    generated_dir = app.config.get("GENERATED_FILES_DIR")
    if generated_dir and not os.path.exists(generated_dir):
        os.makedirs(generated_dir, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .auth.routes import auth_bp
    from .proposals.routes import proposals_bp
    from .health.routes import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(proposals_bp)
    app.register_blueprint(health_bp)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/")
    def index():
        from flask_login import current_user
        from flask import redirect, url_for

        if current_user.is_authenticated:
            return redirect(url_for("proposals.dashboard"))
        return redirect(url_for("auth.login"))

    return app

