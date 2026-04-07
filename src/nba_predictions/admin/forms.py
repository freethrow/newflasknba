from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class SeriesForm(FlaskForm):
    home = StringField("Domaćin", validators=[DataRequired()])
    away = StringField("Gost", validators=[DataRequired()])
    result = StringField("Rezultat", validators=[Optional()])
    open = BooleanField("Otvorena za predikcije")
    season = StringField("Sezona", validators=[DataRequired()])
    is_playin = BooleanField("Play-in utakmica")
    submit = SubmitField("Sačuvaj")


class PredictionAdminForm(FlaskForm):
    predicted = StringField("Predikcija", validators=[Optional()])
    score_made = IntegerField("Poeni", validators=[Optional()])
    submit = SubmitField("Sačuvaj")


class MessageAdminForm(FlaskForm):
    body = TextAreaField("Poruka", validators=[DataRequired()])
    submit = SubmitField("Pošalji")
