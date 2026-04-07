from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Regexp


class PredictionForm(FlaskForm):
    predicted = StringField(
        "Predikcija (npr. 4:2)",
        validators=[
            DataRequired(),
            Regexp(r"^\d:\d$", message="Format mora biti X:Y npr. 4:2"),
        ],
    )
    submit = SubmitField("Pošalji")


class CommentForm(FlaskForm):
    body = TextAreaField("Komentar", validators=[DataRequired()])
    submit = SubmitField("Objavi")


class MessageForm(FlaskForm):
    body = TextAreaField("Poruka adminu", validators=[DataRequired()])
    submit = SubmitField("Pošalji")
