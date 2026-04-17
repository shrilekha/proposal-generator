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
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(proposals_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(admin_bp)

    from .models import User, ModuleSectionMap, SectionTemplate
    from .constants import DEFAULT_MODULE_SECTION_MAP, DEFAULT_SECTION_TEMPLATES

    @app.cli.command("seed-module-sections")
    def seed_module_sections():
        """Seed ModuleSectionMap with default module -> section_key mapping."""
        if ModuleSectionMap.query.first() is not None:
            return
        for module_tag, section_key in DEFAULT_MODULE_SECTION_MAP:
            db.session.add(ModuleSectionMap(module_tag=module_tag, section_key=section_key))
        db.session.commit()
        print("ModuleSectionMap seeded.")

    @app.cli.command("seed-section-templates")
    def seed_section_templates():
        """Seed SectionTemplate with DEFAULT_SECTION_TEMPLATES definitions."""
        if SectionTemplate.query.first() is not None:
            return
        for idx, spec in enumerate(DEFAULT_SECTION_TEMPLATES):
            tmpl = SectionTemplate(
                section_key=spec["section_key"],
                title=spec["title"],
                default_content=spec.get("default_content", ""),
                order_index=idx,
                is_default_enabled=True,
            )
            db.session.add(tmpl)
        db.session.commit()
        print("SectionTemplate seeded from DEFAULT_SECTION_TEMPLATES.")

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

