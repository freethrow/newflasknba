from nba_predictions.extensions import db as _db
from nba_predictions.models import Comment, Prediction, Series


def _login_as(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _make_series(db, open=True, result=None):
    s = Series(home="Lakers", away="Celtics", open=open, result=result)
    db.session.add(s)
    db.session.commit()
    return s


# ---------------------------------------------------------------------------
# Prediction submit
# ---------------------------------------------------------------------------


def test_anonymous_cannot_submit_prediction(client, db):
    s = _make_series(db)
    resp = client.post(
        f"/series/{s.id}", data={"predicted": "4:2"}, follow_redirects=True
    )
    # Should redirect to login
    assert b"Prijavi" in resp.data or resp.status_code == 200
    count = db.session.execute(_db.select(Prediction)).scalars().all()
    assert len(count) == 0
    db.session.delete(s)
    db.session.commit()


def test_user_can_submit_prediction_on_open_series(client, db, regular_user):
    _login_as(client, regular_user)
    s = _make_series(db, open=True)
    resp = client.post(
        f"/series/{s.id}", data={"predicted": "4:2"}, follow_redirects=True
    )
    assert resp.status_code == 200
    p = db.session.execute(
        _db.select(Prediction).filter_by(series_id=s.id, user_id=regular_user.id)
    ).scalar_one_or_none()
    assert p is not None
    assert p.predicted == "4:2"
    db.session.delete(p)
    db.session.delete(s)
    db.session.commit()


def test_user_can_update_existing_prediction(client, db, regular_user):
    _login_as(client, regular_user)
    s = _make_series(db, open=True)
    # Submit initial
    client.post(f"/series/{s.id}", data={"predicted": "4:2"})
    # Update
    client.post(f"/series/{s.id}", data={"predicted": "4:3"}, follow_redirects=True)
    p = db.session.execute(
        _db.select(Prediction).filter_by(series_id=s.id, user_id=regular_user.id)
    ).scalar_one_or_none()
    assert p.predicted == "4:3"
    db.session.delete(p)
    db.session.delete(s)
    db.session.commit()


def test_prediction_rejected_on_closed_series(client, db, regular_user):
    _login_as(client, regular_user)
    s = _make_series(db, open=False, result="4:2")
    resp = client.post(
        f"/series/{s.id}", data={"predicted": "4:2"}, follow_redirects=True
    )
    assert resp.status_code == 200
    p = db.session.execute(
        _db.select(Prediction).filter_by(series_id=s.id, user_id=regular_user.id)
    ).scalar_one_or_none()
    assert p is None
    db.session.delete(s)
    db.session.commit()


def test_series_detail_shows_all_predictions_when_closed(client, db, regular_user):
    _login_as(client, regular_user)
    s = _make_series(db, open=False, result="4:2")
    p = Prediction(series_id=s.id, user_id=regular_user.id, predicted="4:1", score_made=15)
    db.session.add(p)
    db.session.commit()
    resp = client.get(f"/series/{s.id}")
    assert resp.status_code == 200
    assert b"4:1" in resp.data
    db.session.delete(p)
    db.session.delete(s)
    db.session.commit()


def test_my_predictions_page(client, db, regular_user):
    _login_as(client, regular_user)
    s = _make_series(db)
    p = Prediction(series_id=s.id, user_id=regular_user.id, predicted="4:2", score_made=0)
    db.session.add(p)
    db.session.commit()
    resp = client.get("/my-predictions")
    assert resp.status_code == 200
    assert b"Lakers" in resp.data
    db.session.delete(p)
    db.session.delete(s)
    db.session.commit()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def test_post_comment_creates_entry(client, db, regular_user):
    _login_as(client, regular_user)
    s = _make_series(db)
    resp = client.post(
        f"/series/{s.id}/comment",
        data={"body": "Great pick!"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    c = db.session.execute(
        _db.select(Comment).filter_by(body="Great pick!")
    ).scalar_one_or_none()
    assert c is not None
    db.session.delete(c)
    db.session.delete(s)
    db.session.commit()


def test_post_comment_htmx_returns_partial(client, db, regular_user):
    _login_as(client, regular_user)
    s = _make_series(db)
    resp = client.post(
        f"/series/{s.id}/comment",
        data={"body": "HTMX comment"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    # Should be just the partial, not a full page
    assert b"<!DOCTYPE" not in resp.data
    c = db.session.execute(
        _db.select(Comment).filter_by(body="HTMX comment")
    ).scalar_one_or_none()
    if c:
        db.session.delete(c)
    db.session.delete(s)
    db.session.commit()


def test_anonymous_cannot_post_comment(client, db):
    s = _make_series(db)
    resp = client.post(f"/series/{s.id}/comment", data={"body": "anon comment"})
    assert resp.status_code in (302, 401)
    db.session.delete(s)
    db.session.commit()


# ---------------------------------------------------------------------------
# Prediction validation endpoint
# ---------------------------------------------------------------------------


def test_validate_prediction_valid_format(client):
    resp = client.post("/validate/prediction", data={"predicted": "4:2"})
    assert resp.status_code == 200
    assert b"green" in resp.data


def test_validate_prediction_invalid_format(client):
    resp = client.post("/validate/prediction", data={"predicted": "bad"})
    assert resp.status_code == 200
    assert b"red" in resp.data


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def test_leaderboard_fragment_returns_partial(client):
    resp = client.get("/leaderboard/fragment")
    assert resp.status_code == 200
    assert b"<!DOCTYPE" not in resp.data


def test_leaderboard_loads(client, db, regular_user):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Tabela" in resp.data
