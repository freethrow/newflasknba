import pytest
from nba_predictions.extensions import db as _db


def test_login_success(client, regular_user):
    resp = client.post("/auth/login", data={
        "username": "user_test",
        "password": "userpass",
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_login_wrong_password(client, regular_user):
    resp = client.post("/auth/login", data={
        "username": "user_test",
        "password": "wrongpass",
    }, follow_redirects=True)
    assert b"Pogre" in resp.data  # "Pogrešno"


def test_register_creates_user(client, db):
    from nba_predictions.models import User
    resp = client.post("/auth/register", data={
        "username": "newuser99",
        "password": "securepass",
        "password2": "securepass",
    }, follow_redirects=True)
    assert resp.status_code == 200
    u = db.session.execute(
        _db.select(User).filter_by(username="newuser99")
    ).scalar_one_or_none()
    assert u is not None
    # cleanup
    db.session.delete(u)
    db.session.commit()


def test_register_duplicate_username(client, regular_user):
    resp = client.post("/auth/register", data={
        "username": "user_test",
        "password": "securepass",
        "password2": "securepass",
    })
    assert b"zauzeto" in resp.data


def test_register_password_mismatch(client):
    resp = client.post("/auth/register", data={
        "username": "mismatch_user",
        "password": "pass1234",
        "password2": "different",
    })
    assert resp.status_code == 200
    assert b"mismatch_user" not in resp.data or b"Field must be equal" in resp.data


def test_admin_only_route_blocked_for_anonymous(client):
    resp = client.get("/admin/")
    assert resp.status_code in (302, 403)


def test_admin_only_route_blocked_for_regular_user(client, regular_user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(regular_user.id)
        sess["_fresh"] = True
    resp = client.get("/admin/")
    assert resp.status_code == 403


def test_admin_only_route_allowed_for_admin(client, admin_user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)
        sess["_fresh"] = True
    resp = client.get("/admin/")
    assert resp.status_code == 200


def test_logout(client, regular_user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(regular_user.id)
        sess["_fresh"] = True
    resp = client.get("/auth/logout", follow_redirects=True)
    assert resp.status_code == 200


def test_reset_password_request_unknown_user(client):
    resp = client.post("/auth/reset-password-request", data={
        "username": "nonexistent_xyz"
    }, follow_redirects=True)
    assert b"poslan" in resp.data


def test_reset_password_bad_token(client):
    resp = client.get("/auth/reset-password/badtoken", follow_redirects=True)
    assert b"istekao" in resp.data


def test_argon2_password_hash(db):
    from nba_predictions.models import User
    u = User(username="hashtest")
    u.password = "mysecretpass"
    assert u.password_hash.startswith("$argon2")
    assert u.verify_password("mysecretpass")
    assert not u.verify_password("wrongpass")


def test_promote_user_cli(app, regular_user):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["user", "promote", "user_test"])
    assert "admin" in result.output.lower()
    with app.app_context():
        from nba_predictions.models import User
        u = _db.session.execute(
            _db.select(User).filter_by(username="user_test")
        ).scalar_one()
        assert u.is_admin is True
        u.is_admin = False
        _db.session.commit()
