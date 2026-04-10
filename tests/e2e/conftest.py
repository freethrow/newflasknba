"""
E2e test fixtures — runs the Flask app in a background thread against a real SQLite file.
Playwright communicates with it as a real browser would.
"""
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-not-for-prod")
os.environ.setdefault("RESEND_API_KEY", "re_placeholder")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")

E2E_PORT = 5099


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("e2e_db") / "e2e.sqlite")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    from nba_predictions import create_app
    from nba_predictions.extensions import db
    from nba_predictions.models import Series, User

    flask_app = create_app("testing")
    # Keep CSRF disabled (testing config) — simpler for e2e.
    # Real forms still render the token field; it's just not validated.

    with flask_app.app_context():
        db.create_all()
        admin = User(username="admin", is_admin=True, is_active=True)
        admin.password = "admin123"
        regular = User(username="player1", is_active=True)
        regular.password = "player123"
        db.session.add_all([admin, regular])
        db.session.commit()

    return flask_app


@pytest.fixture(scope="session")
def live_server(app):
    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", E2E_PORT, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://127.0.0.1:{E2E_PORT}"
    server.shutdown()


# Override pytest-playwright's base_url fixture so page.goto("/auth/login") works.
@pytest.fixture(scope="session")
def base_url(live_server):
    return live_server


# ── helpers ──────────────────────────────────────────────────────────────────

def login(page, username: str, password: str):
    page.goto("/auth/login")
    page.fill('[name="username"]', username)
    page.fill('[name="password"]', password)
    page.click('[type="submit"]')
    page.wait_for_load_state("networkidle")


def logout(page):
    page.goto("/auth/logout")
    page.wait_for_load_state("networkidle")
