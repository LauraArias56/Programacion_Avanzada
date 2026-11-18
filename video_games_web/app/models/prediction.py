"""Modelo de historial de predicciones."""

from datetime import datetime, timezone

from ..extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform = db.Column(db.String(50), nullable=False, index=True)
    genre = db.Column(db.String(50), nullable=False, index=True)
    publisher = db.Column(db.String(120), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    predicted_sales_millions = db.Column(db.Numeric(12, 4), nullable=False)
    predicted_log_sales = db.Column(db.Numeric(12, 4), nullable=False)
    interval_low = db.Column(db.Numeric(12, 4), nullable=True)
    interval_high = db.Column(db.Numeric(12, 4), nullable=True)
    warnings = db.Column(db.JSON, nullable=False, default=list)
    model_version = db.Column(db.String(40), nullable=False)
    request_id = db.Column(db.String(64), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    user = db.relationship("User", back_populates="predictions")
    vision_prediction = db.relationship(
        "VisionPrediction",
        back_populates="sales_prediction",
        uselist=False,
        foreign_keys="VisionPrediction.prediction_id",
    )

    def __repr__(self) -> str:
        return f"<Prediction {self.id} {self.platform}/{self.genre} {self.year}>"
