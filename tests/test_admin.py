from nba_predictions.extensions import db as _db
from nba_predictions.models import AdminLog, Prediction, Series


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login_as(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _make_series(db):
    s = Series(home="Lakers", away="Celtics")
    db.session.add(s)
    db.session.commit()
    return s


def _make_prediction(db, series, user, predicted="4:2"):
    p = Prediction(series_id=series.id, user_id=user.id, predicted=predicted)
    db.session.add(p)
    db.session.commit()
    return p


# ---------------------------------------------------------------------------
# Permission boundaries
# ---------------------------------------------------------------------------


def test_dashboard_anonymous_redirects(client):
    resp = client.get("/admin/")
    assert resp.status_code in (302, 403)


def test_dashboard_regular_user_forbidden(client, regular_user):
    _login_as(client, regular_user)
    resp = client.get("/admin/")
    assert resp.status_code == 403


def test_dashboard_admin_ok(client, admin_user):
    _login_as(client, admin_user)
    resp = client.get("/admin/")
    assert resp.status_code == 200


def test_log_regular_user_forbidden(client, regular_user):
    _login_as(client, regular_user)
    resp = client.get("/admin/log")
    assert resp.status_code == 403


def test_inbox_regular_user_forbidden(client, regular_user):
    _login_as(client, regular_user)
    resp = client.get("/admin/messages")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Series CRUD
# ---------------------------------------------------------------------------


def test_update_series_changes_result(client, db, admin_user):
    _login_as(client, admin_user)
    s = _make_series(db)
    resp = client.post(f"/admin/series/{s.id}", data={"result": "4:1", "open": "false"})
    assert resp.status_code == 200
    db.session.refresh(s)
    assert s.result == "4:1"
    assert s.open is False
    db.session.delete(s)
    db.session.commit()


def test_update_series_logs_action(client, db, admin_user):
    _login_as(client, admin_user)
    s = _make_series(db)
    client.post(f"/admin/series/{s.id}", data={"result": "4:3", "open": "false"})
    entries = (
        db.session.execute(
            _db.select(AdminLog)
            .filter_by(action="update_series", target_id=s.id)
            .order_by(AdminLog.when.desc())
        )
        .scalars()
        .all()
    )
    assert len(entries) >= 1
    assert "4:3" in entries[0].after
    for e in entries:
        db.session.delete(e)
    db.session.delete(s)
    db.session.commit()


def test_update_series_nonexistent_returns_404(client, db, admin_user):
    _login_as(client, admin_user)
    resp = client.post("/admin/series/99999", data={"result": "4:1"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Prediction CRUD
# ---------------------------------------------------------------------------


def test_update_prediction_changes_score(client, db, admin_user, regular_user):
    _login_as(client, admin_user)
    s = _make_series(db)
    p = _make_prediction(db, s, regular_user)
    resp = client.post(
        f"/admin/series/{s.id}/predictions/{p.id}",
        data={"predicted": "4:3", "score_made": "20"},
    )
    assert resp.status_code == 200
    db.session.refresh(p)
    assert p.predicted == "4:3"
    assert p.score_made == 20
    db.session.delete(p)
    db.session.delete(s)
    db.session.commit()


def test_recalculate_series_updates_scores(client, db, admin_user, regular_user):
    _login_as(client, admin_user)
    s = _make_series(db)
    s.result = "4:2"
    db.session.commit()
    p = _make_prediction(db, s, regular_user, predicted="4:2")

    client.post(f"/admin/series/{s.id}/recalculate", follow_redirects=True)

    db.session.refresh(p)
    assert p.score_made == 25  # exact match: 15 + 10
    db.session.delete(p)
    db.session.delete(s)
    db.session.commit()


def test_recalculate_series_no_result_flashes_warning(client, db, admin_user):
    _login_as(client, admin_user)
    s = _make_series(db)  # no result set
    resp = client.post(f"/admin/series/{s.id}/recalculate", follow_redirects=True)
    assert resp.status_code == 200
    assert b"rezultat" in resp.data
    db.session.delete(s)
    db.session.commit()


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


def test_update_user_promotes_to_admin(client, db, admin_user, regular_user):
    _login_as(client, admin_user)
    resp = client.post(
        f"/admin/users/{regular_user.id}",
        data={"is_admin": "true", "is_active": "true"},
    )
    assert resp.status_code == 200
    db.session.refresh(regular_user)
    assert regular_user.is_admin is True
    # reset
    regular_user.is_admin = False
    db.session.commit()


def test_update_user_deactivates_account(client, db, admin_user, regular_user):
    _login_as(client, admin_user)
    client.post(
        f"/admin/users/{regular_user.id}",
        data={"is_admin": "false", "is_active": "false"},
    )
    db.session.refresh(regular_user)
    assert regular_user.is_active is False
    # restore
    regular_user.is_active = True
    db.session.commit()


# ---------------------------------------------------------------------------
# Admin log
# ---------------------------------------------------------------------------


def test_log_page_renders(client, admin_user):
    _login_as(client, admin_user)
    resp = client.get("/admin/log")
    assert resp.status_code == 200
