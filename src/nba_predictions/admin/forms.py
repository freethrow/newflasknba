from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class SeriesForm(FlaskForm):
    home = StringField("Domaćin", validators=[DataRequired()])
    away = StringField("Gost", validators=[DataRequired()])
    is_playin = BooleanField("Play-in utakmica")
    submit = SubmitField("Dodaj seriju")


class PredictionAdminForm(FlaskForm):
    predicted = StringField("Prognoza", validators=[Optional()])
    score_made = IntegerField("Poeni", validators=[Optional()])
    submit = SubmitField("Sačuvaj")


class MessageAdminForm(FlaskForm):
    body = TextAreaField("Poruka", validators=[DataRequired()])
    submit = SubmitField("Pošalji")
