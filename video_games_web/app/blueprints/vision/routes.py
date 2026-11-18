"""Rutas del modulo de vision: captura, clasificacion e historial."""

import logging

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ...extensions import db
from ...models import VisionPrediction
from ...services.api_client import ApiError, ApiUnavailable, ApiValidationError
from ...services.audit import record_audit
from ...services.vision_client import get_vision_client

bp = Blueprint("vision", __name__, url_prefix="/vision")
logger = logging.getLogger("app.vision")

ALLOWED_SOURCES = {"camera", "upload"}


def _wants_json() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _recent(user_id: int, limit: int = 5) -> list[VisionPrediction]:
    return list(
        db.session.scalars(
            db.select(VisionPrediction)
            .where(VisionPrediction.user_id == user_id)
            .order_by(VisionPrediction.created_at.desc())
            .limit(limit)
        ).all()
    )


def _error_response(message: str, status: int = 422):
    if _wants_json():
        return jsonify({"error": message}), status
    flash(message, "danger")
    return redirect(url_for("vision.index"))


@bp.route("/", strict_slashes=False)
@login_required
def index():
    client = get_vision_client()
    health = None
    info = None
    try:
        health = client.health()
    except ApiError as exc:
        logger.warning("vision_health_unavailable", extra={"error": str(exc)})
    try:
        info = client.model_info()
    except ApiError as exc:
        logger.warning("vision_model_info_unavailable", extra={"error": str(exc)})

    prediction = None
    prediction_id = request.args.get("prediction_id", type=int)
    if prediction_id:
        prediction = db.session.get(VisionPrediction, prediction_id)
        if prediction is None or prediction.user_id != current_user.id:
            abort(404)

    return render_template(
        "vision/index.html",
        health=health,
        info=info,
        prediction=prediction,
        recent=_recent(current_user.id),
        max_upload_mb=current_app.config["VISION_MAX_UPLOAD_MB"],
    )


@bp.route("/predict", methods=["POST"])
@login_required
def predict():
    image = request.files.get("image")
    if image is None or not image.filename:
        return _error_response("Selecciona o captura una imagen antes de predecir.")

    content_type = (image.mimetype or "").lower()
    if content_type not in current_app.config.get(
        "VISION_ALLOWED_CONTENT_TYPES",
        {"image/jpeg", "image/jpg", "image/png", "image/webp"},
    ):
        return _error_response(
            "Formato no soportado. Usa JPG, PNG o WebP.", 415
        )

    data = image.read()
    max_bytes = current_app.config["VISION_MAX_UPLOAD_MB"] * 1024 * 1024
    if not data:
        return _error_response("La imagen esta vacia.")
    if len(data) > max_bytes:
        return _error_response(
            f"La imagen supera el limite de {current_app.config['VISION_MAX_UPLOAD_MB']} MB.",
            413,
        )

    source = (request.form.get("source") or "upload").strip().lower()
    if source not in ALLOWED_SOURCES:
        source = "upload"

    client = get_vision_client()
    try:
        result = client.predict_image(
            data,
            filename=image.filename,
            content_type=content_type,
            top_k=3,
        )
    except ApiValidationError as exc:
        record_audit(
            "vision.prediction_failed",
            status="failure",
            metadata={"source": source, "filename": image.filename},
            error=str(exc),
        )
        db.session.commit()
        logger.warning(
            "vision_prediction_rejected",
            extra={"error": str(exc), "status": exc.status_code or 422},
        )
        return _error_response(str(exc), exc.status_code or 422)
    except ApiUnavailable as exc:
        record_audit(
            "vision.prediction_failed",
            status="failure",
            metadata={"source": source, "filename": image.filename},
            error=str(exc),
        )
        db.session.commit()
        logger.error("vision_api_unavailable", extra={"error": str(exc)})
        if _wants_json():
            return jsonify({"error": str(exc)}), 503
        abort(503)

    prediction_data = result.get("prediction") or {}
    if not prediction_data.get("label"):
        return _error_response("La Vision API devolvio una respuesta incompleta.", 502)

    prediction = VisionPrediction(
        user_id=current_user.id,
        label=prediction_data.get("label", ""),
        label_es=prediction_data.get("label_es") or prediction_data.get("label", ""),
        confidence=float(prediction_data.get("confidence", 0)),
        top_k=prediction_data.get("top_k") or [],
        source=source,
        model_version=result.get("model_version", ""),
        request_id=result.get("request_id"),
        latency_ms=prediction_data.get("latency_ms"),
    )
    db.session.add(prediction)
    record_audit(
        "vision.prediction.created",
        metadata={
            "label": prediction.label,
            "confidence": float(prediction.confidence),
            "source": source,
            "model_version": prediction.model_version,
        },
    )
    db.session.commit()
    logger.info(
        "vision_prediction_created",
        extra={
            "vision_prediction_id": prediction.id,
            "label": prediction.label,
            "confidence": float(prediction.confidence),
        },
    )

    redirect_url = url_for("vision.index", prediction_id=prediction.id)
    if _wants_json():
        return jsonify(
            {
                "prediction_id": prediction.id,
                "label_es": prediction.label_es,
                "confidence": float(prediction.confidence),
                "redirect_url": redirect_url,
            }
        )

    flash("Imagen clasificada correctamente.", "success")
    return redirect(redirect_url)


@bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    label = request.args.get("label", "").strip()

    stmt = db.select(VisionPrediction).where(
        VisionPrediction.user_id == current_user.id
    )
    if label:
        stmt = stmt.where(VisionPrediction.label == label)
    stmt = stmt.order_by(VisionPrediction.created_at.desc())

    pagination = db.paginate(
        stmt,
        page=max(page, 1),
        per_page=current_app.config["VISION_HISTORY_PAGE_SIZE"],
        error_out=False,
    )

    labels = db.session.scalars(
        db.select(VisionPrediction.label)
        .where(VisionPrediction.user_id == current_user.id)
        .distinct()
        .order_by(VisionPrediction.label)
    ).all()

    return render_template(
        "vision/history.html",
        pagination=pagination,
        predictions=pagination.items,
        labels=list(labels),
        filters={"label": label},
    )
