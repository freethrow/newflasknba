from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import csrf, db, limiter
from ..models import Comment, Message, Prediction, Series, User
from ..scoring import calculate_score
from . import main
from .forms import CommentForm, MessageForm, PredictionForm


@main.route("/")
def index():
    season = request.args.get("season", current_app.config["CURRENT_SEASON"])
    users = db.session.execute(db.select(User)).scalars().all()
    leaderboard = []
    for u in users:
        season_score = sum(
            p.score_made or 0
            for p in u.predictions
            if p.series.season == season
        )
        leaderboard.append((u, season_score))
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    seasons = db.session.execute(db.select(Series.season).distinct()).scalars().all()
    return render_template(
        "main/index.html",
        leaderboard=leaderboard,
        seasons=sorted(seasons, reverse=True),
        current_season=season,
    )


@main.route("/leaderboard/fragment")
@limiter.limit("10 per minute")
def leaderboard_fragment():
    season = request.args.get("season", current_app.config["CURRENT_SEASON"])
    users = db.session.execute(db.select(User)).scalars().all()
    leaderboard = []
    for u in users:
        season_score = sum(
            p.score_made or 0
            for p in u.predictions
            if p.series.season == season
        )
        leaderboard.append((u, season_score))
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    return render_template(
        "partials/leaderboard_rows.html",
        leaderboard=leaderboard,
        current_season=season,
    )


@main.route("/series")
def series_list():
    season = request.args.get("season", current_app.config["CURRENT_SEASON"])
    all_series = db.session.execute(
        db.select(Series).filter_by(season=season).order_by(Series.id)
    ).scalars().all()
    user_preds = {}
    if current_user.is_authenticated:
        preds = db.session.execute(
            db.select(Prediction).filter_by(user_id=current_user.id)
        ).scalars().all()
        user_preds = {p.series_id: p for p in preds}
    return render_template(
        "main/series_list.html",
        series_list=all_series,
        user_preds=user_preds,
    )


@main.route("/series/<int:series_id>", methods=["GET", "POST"])
def series_detail(series_id: int):
    series = db.get_or_404(Series, series_id)
    pred_form = PredictionForm()
    comment_form = CommentForm()

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
                pred = Prediction(
                    series=series,
                    user=current_user,
                    predicted=pred_form.predicted.data,
                )
                db.session.add(pred)
            db.session.commit()
            flash("Predikcija sačuvana.", "success")
        else:
            flash("Serija je zatvorena za predikcije.", "warning")
        return redirect(url_for("main.series_detail", series_id=series_id))

    all_preds = []
    if not series.open:
        all_preds = db.session.execute(
            db.select(Prediction).filter_by(series_id=series_id)
        ).scalars().all()

    comments = db.session.execute(
        db.select(Comment).order_by(Comment.created)
    ).scalars().all()

    return render_template(
        "main/series_detail.html",
        series=series,
        pred_form=pred_form,
        comment_form=comment_form,
        existing_pred=existing_pred,
        all_preds=all_preds,
        comments=comments,
    )


@main.route("/series/<int:series_id>/comment", methods=["POST"])
@login_required
def post_comment(series_id: int):
    db.get_or_404(Series, series_id)
    form = CommentForm()
    if form.validate_on_submit():
        c = Comment(user=current_user, body=form.body.data)
        db.session.add(c)
        db.session.commit()
    comments = db.session.execute(
        db.select(Comment).order_by(Comment.created)
    ).scalars().all()
    if request.headers.get("HX-Request"):
        return render_template("partials/comment_list.html", comments=comments)
    return redirect(url_for("main.series_detail", series_id=series_id))


@main.route("/validate/prediction", methods=["POST"])
@csrf.exempt
def validate_prediction():
    import re
    value = request.form.get("predicted", "")
    if re.match(r"^\d:\d$", value):
        return '<span class="text-xs text-green-600">✓</span>'
    return '<span class="text-xs text-red-600">Format mora biti X:Y npr. 4:2</span>'


@main.route("/my-predictions")
@login_required
def my_predictions():
    preds = db.session.execute(
        db.select(Prediction).filter_by(user_id=current_user.id)
    ).scalars().all()
    return render_template("main/my_predictions.html", predictions=preds)


@main.route("/messages")
@login_required
def messages():
    msgs = db.session.execute(
        db.select(Message)
        .filter_by(to_user_id=current_user.id)
        .order_by(Message.created.desc())
    ).scalars().all()
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
    admin = db.session.execute(
        db.select(User).filter_by(is_admin=True)
    ).scalar_one_or_none()
    if not admin:
        flash("Nema dostupnog admina.", "warning")
        return redirect(url_for("main.index"))
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(
            sender=current_user,
            recipient=admin,
            body=form.body.data,
        )
        db.session.add(msg)
        db.session.commit()
        flash("Poruka poslata.", "success")
        return redirect(url_for("main.index"))
    return render_template("main/send_message.html", form=form, admin=admin)
