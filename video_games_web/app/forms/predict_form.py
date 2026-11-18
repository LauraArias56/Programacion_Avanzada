"""Formulario de prediccion de ventas."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class PredictForm(FlaskForm):
    platform = SelectField("Plataforma", validators=[DataRequired()])
    genre = SelectField("Genero", validators=[DataRequired()])
    publisher = StringField(
        "Editorial",
        validators=[Optional(), Length(max=120)],
        default="Other",
        description="Si no aparece en el entrenamiento se agrupa como 'Other'.",
    )
    year = IntegerField(
        "Ano de lanzamiento",
        validators=[DataRequired(), NumberRange(min=1970, max=2030)],
    )
    submit = SubmitField("Predecir ventas")
