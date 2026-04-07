from __future__ import annotations

import click
from flask import Flask

from .config import config
from .extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name: str = "default") -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix="/admin")

    @app.errorhandler(404)
    def page_not_found(e):
        from flask import render_template
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        from flask import render_template
        app.logger.exception(e)
        return render_template("500.html"), 500

    _register_cli(app)
    return app


def _register_cli(app: Flask) -> None:
    @app.cli.command("generate-fake")
    @click.option("--count", default=20, show_default=True)
    def generate_fake(count: int) -> None:
        """Seed fake users."""
        from faker import Faker
        from sqlalchemy.exc import IntegrityError

        from .models import User

        fake = Faker()
        for _ in range(count):
            u = User(username=fake.user_name())
            u.password = u.username
            db.session.add(u)
            try:
                db.session.commit()
                click.echo(f"Added user {u.username}")
            except IntegrityError:
                db.session.rollback()

    @app.cli.group()
    def user():
        """User management commands."""

    @user.command("promote")
    @click.argument("username")
    def promote_user(username: str) -> None:
        """Grant admin rights to USERNAME."""
        from .models import User

        u = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if not u:
            click.echo(f"User '{username}' not found.")
            return
        u.is_admin = True
        db.session.commit()
        click.echo(f"'{username}' is now an admin.")

    @app.cli.group()
    def scores():
        """Score management commands."""

    @scores.command("recalculate")
    def recalculate_scores() -> None:
        """Recompute all score_made and user.score from scratch."""
        from .models import Prediction, User
        from .scoring import calculate_score

        preds = db.session.execute(db.select(Prediction)).scalars().all()
        for pred in preds:
            if pred.series.result and pred.predicted:
                pred.score_made = calculate_score(pred.predicted, pred.series.result)
            else:
                pred.score_made = 0

        users = db.session.execute(db.select(User)).scalars().all()
        for u in users:
            u.score = sum(p.score_made or 0 for p in u.predictions)

        db.session.commit()
        click.echo("All scores recalculated.")
