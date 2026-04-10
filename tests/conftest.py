import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest  # noqa: E402

from nba_predictions import create_app  # noqa: E402
from nba_predictions.extensions import db as _db  # noqa: E402


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()


@pytest.fixture
def admin_user(db):
    from nba_predictions.models import User
    u = User(username="admin_test", is_admin=True, is_active=True)
    u.password = "adminpass"
    db.session.add(u)
    db.session.commit()
    yield u
    db.session.delete(u)
    db.session.commit()


@pytest.fixture
def regular_user(db):
    from nba_predictions.models import User
    u = User(username="user_test", is_active=True)
    u.password = "userpass"
    db.session.add(u)
    db.session.commit()
    yield u
    db.session.delete(u)
    db.session.commit()
