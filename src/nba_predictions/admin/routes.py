from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import AdminLog, Comment, Message, Prediction, Series, User
from ..scoring import calculate_score
from . import admin
from .decorators import admin_required
from .forms import MessageAdminForm, PredictionAdminForm, SeriesForm


def _log(action: str, target_id: int | None, before: str, after: str) -> None:
    entry = AdminLog(
        who=current_user.username,
        action=action,
        target_id=target_id,
        before=before,
        after=after,
    )
    db.session.add(entry)


@admin.route("/")
@login_required
@admin_required
def dashboard():
    series_list = db.session.execute(
        db.select(Series).order_by(Series.id.desc())
    ).scalars().all()
    users = db.session.execute(db.select(User).order_by(User.username)).scalars().all()
    return render_template(
        "admin/dashboard.html", series_list=series_list, users=users
    )


@admin.route("/series/<int:series_id>", methods=["POST"])
@login_required
@admin_required
def update_series(series_id: int):
    series = db.get_or_404(Series, series_id)
    before = f"result={series.result}, open={series.open}"
    series.result = request.form.get("result", series.result) or None
    series.open = request.form.get("open") == "true"
    after = f"result={series.result}, open={series.open}"
    _log("update_series", series.id, before, after)
    db.session.commit()
    return render_template("partials/series_row.html", s=series)


@admin.route("/series/<int:series_id>/predictions")
@login_required
@admin_required
def series_predictions(series_id: int):
    series = db.get_or_404(Series, series_id)
    preds = db.session.execute(
        db.select(Prediction).filter_by(series_id=series_id)
    ).scalars().all()
    return render_template(
        "admin/series_predictions.html", series=series, predictions=preds
    )


@admin.route("/series/<int:series_id>/predictions/<int:pred_id>", methods=["POST"])
@login_required
@admin_required
def update_prediction(series_id: int, pred_id: int):
    pred = db.get_or_404(Prediction, pred_id)
    before = f"predicted={pred.predicted}, score_made={pred.score_made}"
    if request.form.get("predicted"):
        pred.predicted = request.form["predicted"]
    if request.form.get("score_made") is not None and request.form["score_made"] != "":
        pred.score_made = int(request.form["score_made"])
    after = f"predicted={pred.predicted}, score_made={pred.score_made}"
    _log("update_prediction", pred.id, before, after)
    db.session.commit()
    return render_template("partials/prediction_row.html", pred=pred)


@admin.route("/series/<int:series_id>/recalculate", methods=["POST"])
@login_required
@admin_required
def recalculate_series(series_id: int):
    series = db.get_or_404(Series, series_id)
    if not series.result:
        flash("Serija nema rezultat.", "warning")
        return redirect(url_for("admin.series_predictions", series_id=series_id))
    preds = db.session.execute(
        db.select(Prediction).filter_by(series_id=series_id)
    ).scalars().all()
    for pred in preds:
        if pred.predicted:
            pred.score_made = calculate_score(pred.predicted, series.result, is_playin=series.is_playin)
    _log("recalculate_series", series_id, "", f"{len(preds)} predictions updated")
    db.session.commit()
    flash("Poeni ponovo izračunati.", "success")
    return redirect(url_for("admin.series_predictions", series_id=series_id))


@admin.route("/users/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def update_user(user_id: int):
    user = db.get_or_404(User, user_id)
    before = f"is_admin={user.is_admin}, is_active={user.is_active}"
    user.is_admin = request.form.get("is_admin") == "true"
    user.is_active = request.form.get("is_active") == "true"
    after = f"is_admin={user.is_admin}, is_active={user.is_active}"
    _log("update_user", user.id, before, after)
    db.session.commit()
    return render_template("partials/user_row.html", u=user)


@admin.route("/users/<int:user_id>/predictions")
@login_required
@admin_required
def user_predictions(user_id: int):
    user = db.get_or_404(User, user_id)
    preds = db.session.execute(
        db.select(Prediction).filter_by(user_id=user_id)
    ).scalars().all()
    return render_template(
        "admin/user_predictions.html", user=user, predictions=preds
    )


@admin.route("/log")
@login_required
@admin_required
def log():
    entries = db.session.execute(
        db.select(AdminLog).order_by(AdminLog.when.desc()).limit(50)
    ).scalars().all()
    return render_template("admin/log.html", entries=entries)


@admin.route("/messages")
@login_required
@admin_required
def inbox():
    msgs = db.session.execute(
        db.select(Message).order_by(Message.created.desc())
    ).scalars().all()
    for m in msgs:
        if not m.read:
            m.read = True
    db.session.commit()
    return render_template("admin/inbox.html", messages=msgs)


@admin.route("/messages/compose/<int:user_id>")
@login_required
@admin_required
def compose_message(user_id: int):
    recipient = db.get_or_404(User, user_id)
    return render_template("partials/message_row.html", recipient=recipient)


@admin.route("/messages/send/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def send_to_user(user_id: int):
    recipient = db.get_or_404(User, user_id)
    form = MessageAdminForm()
    if form.validate_on_submit():
        msg = Message(
            sender=current_user,
            recipient=recipient,
            body=form.body.data,
        )
        db.session.add(msg)
        _log("send_message", user_id, "", f"to={recipient.username}")
        db.session.commit()
        return render_template("partials/message_row.html", recipient=recipient, sent=True)
    return render_template("partials/message_row.html", recipient=recipient)


@admin.route("/comments/<int:comment_id>", methods=["POST"])
@login_required
@admin_required
def delete_comment(comment_id: int):
    c = db.get_or_404(Comment, comment_id)
    _log("delete_comment", comment_id, c.body[:100], "deleted")
    db.session.delete(c)
    db.session.commit()
    return ""
