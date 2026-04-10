from nba_predictions.extensions import db as _db


def _make_token(app, username: str) -> str:
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return s.dumps(username, salt="password-reset")


def test_reset_request_known_user_flashes_confirmation(app, client, regular_user):
    with app.app_context():
        from nba_predictions.models import User
        u = _db.session.execute(_db.select(User).filter_by(username="user_test")).scalar_one()
        u.email = "user_test@example.com"
        _db.session.commit()
    resp = client.post("/auth/reset-password-request", data={
        "username": "user_test",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"poslan" in resp.data


def test_reset_request_unknown_user_same_message(client):
    """Should not reveal whether the user exists (same flash message)."""
    resp = client.post("/auth/reset-password-request", data={
        "username": "ghost_user_xyz",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"poslan" in resp.data


def test_reset_with_valid_token_changes_password(app, client, regular_user):
    token = _make_token(app, "user_test")
    resp = client.post(f"/auth/reset-password/{token}", data={
        "password": "newpass123",
        "password2": "newpass123",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"resetovana" in resp.data

    # verify new password works
    with app.app_context():
        from nba_predictions.models import User
        u = _db.session.execute(
            _db.select(User).filter_by(username="user_test")
        ).scalar_one()
        assert u.verify_password("newpass123")
        # restore original password so fixture teardown can delete cleanly
        u.password = "userpass"
        _db.session.commit()


def test_reset_with_bad_token_shows_error(client):
    resp = client.get("/auth/reset-password/notavalidtoken", follow_redirects=True)
    assert resp.status_code == 200
    assert b"istekao" in resp.data


def test_reset_token_verifies_correct_user(app, regular_user):
    token = _make_token(app, "user_test")
    with app.app_context():
        from nba_predictions.auth.routes import _verify_reset_token
        username = _verify_reset_token(token)
    assert username == "user_test"


def test_reset_token_wrong_salt_invalid(app):
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    bad_token = s.dumps("user_test", salt="wrong-salt")
    with app.app_context():
        from nba_predictions.auth.routes import _verify_reset_token
        assert _verify_reset_token(bad_token) is None
