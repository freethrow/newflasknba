from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import csrf, db, limiter
from ..models import Comment, Message, Prediction, Series, User
from . import main
from .forms import (
    PLAYIN_CHOICES,
    REGULAR_CHOICES,
    MessageForm,
    PredictionForm,
)


@main.route("/")
def index():
    users = db.session.execute(db.select(User)).scalars().all()
    leaderboard = sorted(
        [(u, u.total) for u in users],
        key=lambda x: x[1],
        reverse=True,
    )
    return render_template("main/index.html", leaderboard=leaderboard)


@main.route("/leaderboard/fragment")
@limiter.limit("20 per minute")
def leaderboard_fragment():
    users = db.session.execute(db.select(User)).scalars().all()
    leaderboard = sorted(
        [(u, u.total) for u in users],
        key=lambda x: x[1],
        reverse=True,
    )
    return render_template("partials/leaderboard_rows.html", leaderboard=leaderboard)


@main.route("/series")
def series_list():
    all_series = (
        db.session.execute(db.select(Series).order_by(Series.id)).scalars().all()
    )
    user_preds = {}
    if current_user.is_authenticated:
        preds = (
            db.session.execute(db.select(Prediction).filter_by(user_id=current_user.id))
            .scalars()
            .all()
        )
        user_preds = {p.series_id: p for p in preds}
    return render_template(
        "main/series_list.html",
        series_list=all_series,
        user_preds=user_preds,
    )


def _make_pred_form(series):
    """Return a PredictionForm with choices set for this series type."""
    form = PredictionForm()
    form.predicted.choices = PLAYIN_CHOICES if series.is_playin else REGULAR_CHOICES
    return form


@main.route("/series/<int:series_id>", methods=["GET", "POST"])
def series_detail(series_id: int):
    series = db.get_or_404(Series, series_id)
    pred_form = _make_pred_form(series)

    existing_pred = None
    if current_user.is_authenticated:
        existing_pred = db.session.execute(
            db.select(Prediction).filter_by(
                series_id=series_id, user_id=current_user.id
            )
        ).scalar_one_or_none()

    if pred_form.validate_on_submit() and current_user.is_authenticated:
        if series.open:
            if existing_pred:
                existing_pred.predicted = pred_form.predicted.data
            else:
                existing_pred = Prediction(
                    series=series,
                    user=current_user,
                    predicted=pred_form.predicted.data,
                )
                db.session.add(existing_pred)
            db.session.commit()
            # HTMX: return just the prediction section partial
            if request.headers.get("HX-Request"):
                return render_template(
                    "partials/prediction_section.html",
                    series=series,
                    pred_form=_make_pred_form(series),
                    existing_pred=existing_pred,
                    saved=True,
                )
            flash("Predikcija sačuvana.", "success")
        else:
            flash("Serija je zatvorena za predikcije.", "warning")
        return redirect(url_for("main.series_detail", series_id=series_id))

    all_preds = []
    if not series.open:
        all_preds = (
            db.session.execute(db.select(Prediction).filter_by(series_id=series_id))
            .scalars()
            .all()
        )

    return render_template(
        "main/series_detail.html",
        series=series,
        pred_form=pred_form,
        existing_pred=existing_pred,
        all_preds=all_preds,
    )


@main.route("/comments")
@login_required
def comments():
    all_comments = (
        db.session.execute(db.select(Comment).order_by(Comment.created.desc()))
        .scalars()
        .all()
    )
    return render_template("main/comments.html", comments=all_comments)


@main.route("/comments/post", methods=["POST"])
@login_required
def post_comment():
    from .forms import CommentForm

    form = CommentForm()
    if form.validate_on_submit():
        c = Comment(user=current_user, body=form.body.data)
        db.session.add(c)
        db.session.commit()

    all_comments = (
        db.session.execute(db.select(Comment).order_by(Comment.created.desc()))
        .scalars()
        .all()
    )
    if request.headers.get("HX-Request"):
        return render_template("partials/comment_list.html", comments=all_comments)
    return redirect(url_for("main.comments"))


@main.route("/validate/prediction", methods=["POST"])
@csrf.exempt
def validate_prediction():
    import re

    value = request.form.get("predicted", "")
    if re.match(r"^\d:\d$", value):
        return '<span class="text-xs text-green-600">✓</span>'
    return '<span class="text-xs text-red-600">Format mora biti X:Y npr. 4:2</span>'


@main.route("/player/<username>")
@login_required
def player_profile(username: str):
    user = db.session.execute(
        db.select(User).filter_by(username=username)
    ).scalar_one_or_none()
    if user is None:
        abort(404)
    # Only show predictions for closed series that have a final result
    preds = [p for p in user.predictions if not p.series.open and p.series.result]
    preds.sort(key=lambda p: p.series.id)
    return render_template(
        "main/player_profile.html", profile_user=user, predictions=preds
    )


@main.route("/my-predictions")
@login_required
def my_predictions():
    preds = (
        db.session.execute(db.select(Prediction).filter_by(user_id=current_user.id))
        .scalars()
        .all()
    )
    return render_template("main/my_predictions.html", predictions=preds)


@main.route("/messages")
@login_required
def messages():
    msgs = (
        db.session.execute(
            db.select(Message)
            .filter_by(to_user_id=current_user.id)
            .order_by(Message.created.desc())
        )
        .scalars()
        .all()
    )
    for m in msgs:
        if not m.read:
            m.read = True
    db.session.commit()
    return render_template("main/messages.html", messages=msgs)


@main.route("/messages/send", methods=["GET", "POST"])
@login_required
def send_message():
    if current_user.is_admin:
        abort(403)
    admins = (
        db.session.execute(db.select(User).filter_by(is_admin=True)).scalars().all()
    )
    if not admins:
        flash("Nema dostupnog admina.", "warning")
        return redirect(url_for("main.index"))
    form = MessageForm()
    if form.validate_on_submit():
        for admin in admins:
            db.session.add(
                Message(
                    sender=current_user,
                    recipient=admin,
                    body=form.body.data,
                )
            )
        db.session.commit()
        flash("Poruka poslata.", "success")
        return redirect(url_for("main.index"))
    return render_template("main/send_message.html", form=form)
