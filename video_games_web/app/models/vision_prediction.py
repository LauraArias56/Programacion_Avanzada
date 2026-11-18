"""Modelo de historial de inferencias de vision."""

from datetime import datetime, timezone

from ..extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VisionPrediction(db.Model):
    __tablename__ = "vision_predictions"
    __table_args__ = (
        db.UniqueConstraint(
            "prediction_id", name="uq_vision_predictions_prediction_id"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label = db.Column(db.String(40), nullable=False, index=True)
    label_es = db.Column(db.String(40), nullable=False, index=True)
    confidence = db.Column(db.Numeric(6, 4), nullable=False)
    top_k = db.Column(db.JSON, nullable=False, default=list)
    theme = db.Column(db.String(120), nullable=True)
    source = db.Column(db.String(20), nullable=False, default="upload")
    model_version = db.Column(db.String(60), nullable=False)
    request_id = db.Column(db.String(64), nullable=True)
    latency_ms = db.Column(db.Float, nullable=True)
    prediction_id = db.Column(
        db.Integer,
        db.ForeignKey("predictions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    user = db.relationship("User", back_populates="vision_predictions")
    sales_prediction = db.relationship(
        "Prediction",
        back_populates="vision_prediction",
        foreign_keys=[prediction_id],
    )

    def __repr__(self) -> str:
        return f"<VisionPrediction {self.id} {self.label_es} {self.confidence}>"
