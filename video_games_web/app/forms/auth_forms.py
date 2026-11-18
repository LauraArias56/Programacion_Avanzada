"""Formularios de registro e inicio de sesion."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegisterForm(FlaskForm):
    username = StringField(
        "Usuario", validators=[DataRequired(), Length(min=3, max=80)]
    )
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=255)]
    )
    password = PasswordField(
        "Contrasena", validators=[DataRequired(), Length(min=8, max=128)]
    )
    confirm = PasswordField(
        "Repetir contrasena",
        validators=[
            DataRequired(),
            EqualTo("password", message="Las contrasenas no coinciden."),
        ],
    )
    submit = SubmitField("Crear cuenta")


class LoginForm(FlaskForm):
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=255)]
    )
    password = PasswordField(
        "Contrasena", validators=[DataRequired(), Length(max=128)]
    )
    remember = BooleanField("Recordarme")
    submit = SubmitField("Entrar")
