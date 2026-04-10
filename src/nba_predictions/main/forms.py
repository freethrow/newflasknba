from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired

REGULAR_CHOICES = [
    ("4:0", "4:0"),
    ("4:1", "4:1"),
    ("4:2", "4:2"),
    ("4:3", "4:3"),
    ("3:4", "3:4"),
    ("2:4", "2:4"),
    ("1:4", "1:4"),
    ("0:4", "0:4"),
]

PLAYIN_CHOICES = [
    ("1:0", "1:0 (pobeda domaćina)"),
    ("0:1", "0:1 (pobeda gosta)"),
]


class PredictionForm(FlaskForm):
    predicted = SelectField("Predikcija", validators=[DataRequired()], choices=[])
    submit = SubmitField("Pošalji")


class CommentForm(FlaskForm):
    body = TextAreaField("Komentar", validators=[DataRequired()])
    submit = SubmitField("Objavi")


class MessageForm(FlaskForm):
    body = TextAreaField("Poruka adminu", validators=[DataRequired()])
    submit = SubmitField("Pošalji")
