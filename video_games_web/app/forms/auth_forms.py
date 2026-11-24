"""Formularios de registro e inicio de sesion."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

MENSAJE_CONTRASENA = "La contraseña debe tener 8 caracteres como mínimo."


class RegisterForm(FlaskForm):
    username = StringField(
        "Usuario", validators=[DataRequired(), Length(min=3, max=80)]
    )
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=255)]
    )
    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(message="La contraseña es obligatoria."),
            Length(min=8, max=128, message=MENSAJE_CONTRASENA),
        ],
        description="Mínimo 8 caracteres.",
    )
    confirm = PasswordField(
        "Repetir contraseña",
        validators=[
            DataRequired(message="Debes repetir la contraseña."),
            Length(min=8, max=128, message=MENSAJE_CONTRASENA),
            EqualTo("password", message="Las contraseñas no coinciden."),
        ],
    )
    submit = SubmitField("Crear cuenta")


class LoginForm(FlaskForm):
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=255)]
    )
    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(message="La contraseña es obligatoria."),
            Length(min=8, max=128, message=MENSAJE_CONTRASENA),
        ],
    )
    remember = BooleanField("Recordarme")
    submit = SubmitField("Entrar")
