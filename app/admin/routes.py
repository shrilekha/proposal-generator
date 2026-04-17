from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import SectionTemplate, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        abort(403)


@admin_bp.route("/sections", methods=["GET", "POST"])
@login_required
def manage_sections():
    _require_admin()

    if request.method == "POST":
        # Update existing templates
        template_ids = request.form.getlist("template_id")
        for idx, tid in enumerate(template_ids):
            template = SectionTemplate.query.get(int(tid))
            if not template:
                continue
            template.section_key = request.form.get(f"section_key_{tid}", template.section_key)
            template.title = request.form.get(f"title_{tid}", template.title)
            template.default_content = request.form.get(f"content_{tid}", template.default_content)
            template.order_index = idx
            template.is_default_enabled = request.form.get(f"enabled_{tid}") == "on"

        # Optionally create a new template row if provided
        new_key = request.form.get("new_section_key", "").strip()
        new_title = request.form.get("new_title", "").strip()
        new_content = request.form.get("new_content", "").strip()
        if new_key and new_title:
            exists = SectionTemplate.query.filter_by(section_key=new_key).first()
            if exists:
                flash(f"Section key '{new_key}' already exists.", "warning")
            else:
                max_order = db.session.query(db.func.coalesce(db.func.max(SectionTemplate.order_index), 0)).scalar()
                tmpl = SectionTemplate(
                    section_key=new_key,
                    title=new_title,
                    default_content=new_content,
                    order_index=max_order + 1,
                    is_default_enabled=True,
                )
                db.session.add(tmpl)

        db.session.commit()
        flash("Section templates saved.", "success")
        return redirect(url_for("admin.manage_sections"))

    templates = SectionTemplate.query.order_by(SectionTemplate.order_index).all()
    return render_template("admin/section_templates.html", templates=templates)


@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
def manage_users():
    _require_admin()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "presales").strip() or "presales"

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
        else:
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash("A user with that email already exists.", "warning")
            else:
                user = User(name=name, email=email, role=role, is_active=True)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash(f"{role.capitalize()} user created.", "success")
        return redirect(url_for("admin.manage_users"))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)

