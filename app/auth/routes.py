from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user, current_user

from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("proposals.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email, is_active=True).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password", "danger")
            return render_template("auth/login.html")

        login_user(user)
        return redirect(url_for("proposals.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/init-admin", methods=["GET", "POST"])
def init_admin():
    # Simple bootstrap route to create the first admin user.
    # In production, restrict this further (e.g., IP allowlist).
    if User.query.filter_by(role="admin").first():
        flash("Admin user already exists.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/init_admin.html")

        user = User(name=name, email=email, role="admin", is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Admin user created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/init_admin.html")

