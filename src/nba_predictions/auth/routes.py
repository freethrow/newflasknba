from flask import flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..extensions import db, limiter
from ..models import User
from . import auth
from .forms import (
    LoginForm,
    PasswordResetForm,
    PasswordResetRequestForm,
    RegistrationForm,
)


def _make_reset_token(username: str) -> str:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(username, salt="password-reset")


def _verify_reset_token(token: str, max_age: int = 3600) -> str | None:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        username = s.loads(token, salt="password-reset", max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    return username


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(username=form.username.data)
        ).scalar_one_or_none()
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(request.args.get("next") or url_for("main.index"))
        flash("Pogrešno korisničko ime ili lozinka.", "danger")
    return render_template("auth/login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data or None)
        user.password = form.password.data
        db.session.add(user)
        db.session.commit()
        flash("Registracija uspešna. Možeš se prijaviti.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth.route("/reset-password-request", methods=["GET", "POST"])
def reset_password_request():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(username=form.username.data)
        ).scalar_one_or_none()
        if user and not user.email:
            flash("Ovaj nalog nema email adresu. Kontaktuj admina.", "warning")
            return redirect(url_for("auth.login"))
        if user and user.email:
            token = _make_reset_token(user.username)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            try:
                from ..mail import send_password_reset

                send_password_reset(user.email, reset_url)
            except Exception as e:
                current_app.logger.exception("Failed to send reset email")
                if current_app.debug:
                    raise
        flash("Ako korisnik postoji, poslan je link za reset.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_request.html", form=form)


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    username = _verify_reset_token(token)
    if not username:
        flash("Link je istekao ili je neispravan.", "danger")
        return redirect(url_for("auth.reset_password_request"))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if user:
            user.password = form.password.data
            db.session.commit()
            flash("Lozinka resetovana. Možeš se prijaviti.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)
