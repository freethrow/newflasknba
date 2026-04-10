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

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("403.html"), 403

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
    _auto_create_db(app)
    return app


def _auto_create_db(app: Flask) -> None:
    """Create DB tables on first run if the file doesn't exist yet.

    Uses db.create_all() + stamps the Alembic head so subsequent
    `flask db upgrade` calls know the schema is already current.
    Only runs for file-backed SQLite; skips in-memory test DBs.
    """
    import os

    from sqlalchemy.engine import make_url

    db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if ":memory:" in db_url:
        return

    # make_url handles Windows paths (D:\...) correctly unlike urlparse
    db_path = make_url(db_url).database
    if not db_path or db_path == ":memory:":
        return

    if not os.path.exists(db_path):
        with app.app_context():
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            db.create_all()
            # Stamp Alembic so it knows this schema == current head
            from flask_migrate import stamp
            stamp()
            # Seed the default admin account
            from .models import User
            admin = User(
                username="freethrow",
                email="freethrowrs@gmail.com",
                is_admin=True,
                is_active=True,
            )
            admin.password = "135marko"
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Database created at %s — admin user 'freethrow' added", db_path)


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create the database and apply all migrations.

        Safe to run on an existing database — Alembic will only apply
        missing migrations. On a brand-new install this creates all tables.
        """
        from flask_migrate import upgrade
        upgrade()
        click.echo("Database ready.")

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

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, default=False, help="Drop all data first.")
    def seed(reset: bool) -> None:
        """Create admin user (admin/admin) and fake series for local dev."""
        from sqlalchemy.exc import IntegrityError

        from .models import Prediction, Series, User
        from .scoring import calculate_score

        if reset:
            db.session.execute(db.text("DELETE FROM predictions"))
            db.session.execute(db.text("DELETE FROM series"))
            db.session.execute(db.text("DELETE FROM users"))
            db.session.commit()
            click.echo("Cleared all data.")

        # Admin user
        existing = db.session.execute(
            db.select(User).filter_by(username="admin")
        ).scalar_one_or_none()
        if not existing:
            admin = User(username="admin", is_admin=True, is_active=True)
            admin.password = "admin"
            db.session.add(admin)
            try:
                db.session.commit()
                click.echo("Created admin / admin")
            except IntegrityError:
                db.session.rollback()
        else:
            click.echo("admin user already exists")
            admin = existing

        # A few regular users
        test_users = []
        for uname in ["marko", "petar", "ana", "nikola", "jovana"]:
            u = db.session.execute(
                db.select(User).filter_by(username=uname)
            ).scalar_one_or_none()
            if not u:
                u = User(username=uname, is_active=True)
                u.password = uname
                db.session.add(u)
                try:
                    db.session.commit()
                    click.echo(f"Created user {uname}")
                except IntegrityError:
                    db.session.rollback()
            test_users.append(u)

        # Fake series — mix of open, closed, and play-in
        series_data = [
            # (home, away, open, result, is_playin)
            ("Oklahoma City Thunder", "Memphis Grizzlies", False, "4:1", False),
            ("Boston Celtics", "Miami Heat", False, "4:2", False),
            ("Denver Nuggets", "Los Angeles Lakers", False, "4:3", False),
            ("Minnesota Timberwolves", "Golden State Warriors", True, None, False),
            ("Cleveland Cavaliers", "Orlando Magic", True, None, False),
            ("New York Knicks", "Philadelphia 76ers", True, None, False),
            # Play-in
            ("Chicago Bulls", "Atlanta Hawks", False, "1:0", True),
            ("Sacramento Kings", "Golden State Warriors", True, None, True),
        ]

        created_series = []
        for home, away, open_, result, is_playin in series_data:
            existing_s = db.session.execute(
                db.select(Series).filter_by(home=home, away=away)
            ).scalar_one_or_none()
            if not existing_s:
                s = Series(
                    home=home,
                    away=away,
                    open=open_,
                    result=result,
                    is_playin=is_playin,
                )
                db.session.add(s)
                db.session.commit()
                click.echo(f"Created series: {home} vs {away}")
                created_series.append(s)
            else:
                created_series.append(existing_s)

        # Add some predictions for closed series
        import random

        random.seed(42)
        pred_options = ["4:0", "4:1", "4:2", "4:3", "3:4", "2:4", "1:4", "0:4"]
        playin_options = ["1:0", "0:1"]

        for s in created_series:
            if s.open:
                continue
            options = playin_options if s.is_playin else pred_options
            for u in test_users:
                existing_p = db.session.execute(
                    db.select(Prediction).filter_by(series_id=s.id, user_id=u.id)
                ).scalar_one_or_none()
                if not existing_p:
                    predicted = random.choice(options)
                    score = 0
                    if s.result:
                        score = calculate_score(predicted, s.result, is_playin=s.is_playin)
                    p = Prediction(
                        series_id=s.id,
                        user_id=u.id,
                        predicted=predicted,
                        score_made=score,
                    )
                    db.session.add(p)
            db.session.commit()

        # Update user totals
        all_users = db.session.execute(db.select(User)).scalars().all()
        for u in all_users:
            u.score = sum(p.score_made or 0 for p in u.predictions)
        db.session.commit()

        click.echo("Seed complete. Run the app and visit http://localhost:5000")

    @app.cli.command("backup")
    @click.argument("dest", default="", required=False)
    def backup_db(dest: str) -> None:
        """Back up the SQLite database.

        DEST is the output path. Defaults to ~/backups/nba-YYYY-MM-DD.sqlite.
        """
        import subprocess
        from datetime import date
        from pathlib import Path
        from urllib.parse import urlparse

        db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        parsed = urlparse(db_url)
        # sqlite:////absolute/path  → path is parsed.path
        db_path = parsed.path
        if not db_path or ":memory:" in db_path:
            click.echo("No file-based DATABASE_URL configured — nothing to back up.", err=True)
            raise SystemExit(1)

        if not dest:
            backup_dir = Path.home() / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            dest = str(backup_dir / f"nba-{date.today()}.sqlite")

        result = subprocess.run(
            ["sqlite3", db_path, f".backup {dest}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            click.echo(f"Backup failed: {result.stderr}", err=True)
            raise SystemExit(1)

        click.echo(f"Backup written to {dest}")

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
                pred.score_made = calculate_score(pred.predicted, pred.series.result, is_playin=pred.series.is_playin)
            else:
                pred.score_made = 0

        users = db.session.execute(db.select(User)).scalars().all()
        for u in users:
            u.score = sum(p.score_made or 0 for p in u.predictions)

        db.session.commit()
        click.echo("All scores recalculated.")
