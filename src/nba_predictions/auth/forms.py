from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    ValidationError,
)

from ..extensions import db


class LoginForm(FlaskForm):
    username = StringField("Korisničko ime", validators=[DataRequired()])
    password = PasswordField("Lozinka", validators=[DataRequired()])
    remember_me = BooleanField("Zapamti me")
    submit = SubmitField("Prijavi se")


class RegistrationForm(FlaskForm):
    username = StringField("Korisničko ime", validators=[DataRequired(), Length(3, 64)])
    email = EmailField(
        "Email (za reset lozinke)", validators=[Optional(), Email(), Length(max=120)]
    )
    password = PasswordField("Lozinka", validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        "Potvrdi lozinku", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Registruj se")

    def validate_username(self, field):
        from ..models import User

        if db.session.execute(
            db.select(User).filter_by(username=field.data)
        ).scalar_one_or_none():
            raise ValidationError("Korisničko ime je zauzeto.")

    def validate_email(self, field):
        if not field.data:
            return
        from ..models import User

        if db.session.execute(
            db.select(User).filter_by(email=field.data)
        ).scalar_one_or_none():
            raise ValidationError("Email je već zauzet.")


class PasswordResetRequestForm(FlaskForm):
    username = StringField("Korisničko ime", validators=[DataRequired()])
    submit = SubmitField("Pošalji link za reset")


class PasswordResetForm(FlaskForm):
    password = PasswordField("Nova lozinka", validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        "Potvrdi lozinku", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Resetuj lozinku")
