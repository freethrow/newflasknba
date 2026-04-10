from nba_predictions.extensions import db as _db
from nba_predictions.models import Message


def _login_as(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


# ---------------------------------------------------------------------------
# User → Admin messaging
# ---------------------------------------------------------------------------


def test_send_message_page_requires_login(client):
    resp = client.get("/messages/send")
    assert resp.status_code in (302, 401)


def test_send_message_blocked_for_admin(client, admin_user):
    """Admins must not send via the user-facing form (admin has its own endpoint)."""
    _login_as(client, admin_user)
    resp = client.get("/messages/send")
    assert resp.status_code == 403


def test_send_message_page_visible_to_regular_user(client, regular_user, admin_user):
    _login_as(client, regular_user)
    resp = client.get("/messages/send")
    assert resp.status_code == 200


def test_regular_user_can_send_message_to_admin(client, db, regular_user, admin_user):
    _login_as(client, regular_user)
    resp = client.post(
        "/messages/send",
        data={"body": "Hello admin!"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    msg = db.session.execute(
        _db.select(Message).filter_by(
            from_user_id=regular_user.id, to_user_id=admin_user.id
        )
    ).scalar_one_or_none()
    assert msg is not None
    assert msg.body == "Hello admin!"
    db.session.delete(msg)
    db.session.commit()


def test_messages_inbox_requires_login(client):
    resp = client.get("/messages")
    assert resp.status_code in (302, 401)


def test_messages_inbox_visible_to_user(client, regular_user):
    _login_as(client, regular_user)
    resp = client.get("/messages")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin → User messaging
# ---------------------------------------------------------------------------


def test_admin_send_to_user_blocked_for_regular(client, regular_user):
    _login_as(client, regular_user)
    resp = client.post(
        f"/admin/messages/send/{regular_user.id}", data={"body": "hi"}
    )
    assert resp.status_code == 403


def test_admin_send_to_user_creates_message(client, db, admin_user, regular_user):
    _login_as(client, admin_user)
    resp = client.post(
        f"/admin/messages/send/{regular_user.id}",
        data={"body": "Admin says hi"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    msg = db.session.execute(
        _db.select(Message).filter_by(
            from_user_id=admin_user.id, to_user_id=regular_user.id
        )
    ).scalar_one_or_none()
    assert msg is not None
    assert msg.body == "Admin says hi"
    db.session.delete(msg)
    db.session.commit()


def test_admin_inbox_shows_unread_messages(client, db, admin_user, regular_user):
    msg = Message(
        from_user_id=regular_user.id,
        to_user_id=admin_user.id,
        body="Test message",
        read=False,
    )
    db.session.add(msg)
    db.session.commit()

    _login_as(client, admin_user)
    resp = client.get("/admin/messages")
    assert resp.status_code == 200
    assert b"Test message" in resp.data

    db.session.refresh(msg)
    assert msg.read is True
    db.session.delete(msg)
    db.session.commit()


def test_no_user_to_user_messaging(client, db, regular_user, admin_user):
    """Regular users cannot send messages to other regular users."""
    _login_as(client, regular_user)
    # The only send endpoint for users posts to /messages/send which
    # always routes to the admin; there's no endpoint accepting a user_id target.
    # Verify the admin-side send endpoint is forbidden for non-admins.
    resp = client.post(
        f"/admin/messages/send/{regular_user.id}", data={"body": "user to user"}
    )
    assert resp.status_code == 403
