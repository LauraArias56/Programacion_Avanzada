"""Rutas del modulo de vision: captura, clasificacion, ventas e historial."""

import logging

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from ...extensions import db
from ...models import Prediction, VisionPrediction
from ...services.api_client import (
    ApiError,
    ApiUnavailable,
    ApiValidationError,
    get_api_client,
)
from ...services.audit import record_audit
from ...services.game_profile import infer_game_profile, theme_for_label
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
            .options(selectinload(VisionPrediction.sales_prediction))
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


def _sales_unavailable(error: str):
    if _wants_json():
        return jsonify({"error": error}), 503
    abort(503)


def _payload(profile: dict) -> dict:
    return {
        "platform": profile["platform"],
        "genre": profile["genre"],
        "publisher": profile["publisher"],
        "year": int(profile["year"]),
    }


def _apply_sales_result(
    prediction: Prediction, payload: dict, result: dict
) -> Prediction:
    data = result.get("prediction") or {}
    interval = data.get("interval_95_millions") or [None, None]

    prediction.platform = payload["platform"]
    prediction.genre = payload["genre"]
    prediction.publisher = payload["publisher"]
    prediction.year = payload["year"]
    prediction.predicted_sales_millions = data.get("predicted_sales_millions", 0)
    prediction.predicted_log_sales = data.get("predicted_log_sales", 0)
    prediction.interval_low = interval[0]
    prediction.interval_high = interval[1] if len(interval) > 1 else None
    prediction.warnings = data.get("warnings", [])
    prediction.model_version = result.get("model_version", "")
    prediction.request_id = getattr(g, "request_id", None)
    return prediction


def _sales_response(vision: VisionPrediction, sale: Prediction) -> dict:
    return {
        "prediction_id": vision.id,
        "label_es": vision.label_es,
        "confidence": float(vision.confidence),
        "theme": vision.theme or theme_for_label(vision.label),
        "profile": {
            "platform": sale.platform,
            "genre": sale.genre,
            "publisher": sale.publisher,
            "year": sale.year,
        },
        "predicted_sales_millions": float(sale.predicted_sales_millions),
        "interval_95_millions": [
            float(sale.interval_low or 0),
            float(sale.interval_high or 0),
        ],
        "redirect_url": url_for("vision.index", prediction_id=vision.id),
    }


@bp.route("/", strict_slashes=False)
@login_required
def index():
    vision_client = get_vision_client()
    health = None
    info = None
    try:
        health = vision_client.health()
    except ApiError as exc:
        logger.warning("vision_health_unavailable", extra={"error": str(exc)})
    try:
        info = vision_client.model_info()
    except ApiError as exc:
        logger.warning("vision_model_info_unavailable", extra={"error": str(exc)})

    api = get_api_client()
    sales_health = None
    sales_info = None
    try:
        sales_health = api.health()
    except ApiError as exc:
        logger.warning("sales_health_unavailable", extra={"error": str(exc)})
    try:
        sales_info = api.model_info()
    except ApiError as exc:
        logger.warning("sales_model_info_unavailable", extra={"error": str(exc)})

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
        sales_health=sales_health,
        sales_info=sales_info,
        prediction=prediction,
        prediction_theme=(
            prediction.theme or theme_for_label(prediction.label)
            if prediction
            else None
        ),
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
        return _error_response("Formato no soportado. Usa JPG, PNG o WebP.", 415)

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

    vision_client = get_vision_client()
    try:
        result = vision_client.predict_image(
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
        return _sales_unavailable(str(exc))

    prediction_data = result.get("prediction") or {}
    label = prediction_data.get("label")
    if not label:
        return _error_response("La Vision API devolvio una respuesta incompleta.", 502)

    api = get_api_client()
    try:
        sales_info = api.model_info()
    except ApiError as exc:
        record_audit(
            "vision.prediction_failed",
            status="failure",
            metadata={
                "source": source,
                "filename": image.filename,
                "stage": "sales_model_info",
                "label": label,
            },
            error=str(exc),
        )
        db.session.commit()
        logger.error("sales_model_info_unavailable", extra={"error": str(exc)})
        return _sales_unavailable(
            "La imagen se clasifico, pero la API de ventas no esta disponible."
        )

    profile = infer_game_profile(label, sales_info)
    payload = _payload(profile)

    try:
        sales_result = api.predict(payload)
    except ApiValidationError as exc:
        record_audit(
            "vision.prediction_failed",
            status="failure",
            metadata={
                "source": source,
                "filename": image.filename,
                "stage": "sales_prediction",
                "label": label,
                "profile": profile,
            },
            error=str(exc),
        )
        db.session.commit()
        logger.warning(
            "sales_prediction_rejected",
            extra={"error": str(exc), "profile": profile},
        )
        return _error_response(
            "El perfil inferido no es valido para el modelo de ventas. "
            "Ajusta los datos manualmente.",
            422,
        )
    except ApiUnavailable as exc:
        record_audit(
            "vision.prediction_failed",
            status="failure",
            metadata={
                "source": source,
                "filename": image.filename,
                "stage": "sales_prediction",
                "label": label,
                "profile": profile,
            },
            error=str(exc),
        )
        db.session.commit()
        logger.error("sales_api_unavailable", extra={"error": str(exc)})
        return _sales_unavailable(
            "La imagen se clasifico, pero no se pudo consultar la API de ventas."
        )

    sale = Prediction(user_id=current_user.id)
    _apply_sales_result(sale, payload, sales_result)
    db.session.add(sale)
    db.session.flush()

    prediction = VisionPrediction(
        user_id=current_user.id,
        label=label,
        label_es=prediction_data.get("label_es") or label,
        confidence=float(prediction_data.get("confidence", 0)),
        top_k=prediction_data.get("top_k") or [],
        theme=profile["theme"],
        source=source,
        model_version=result.get("model_version", ""),
        request_id=result.get("request_id"),
        latency_ms=prediction_data.get("latency_ms"),
        prediction_id=sale.id,
    )
    db.session.add(prediction)
    db.session.flush()

    record_audit(
        "vision.prediction.created",
        metadata={
            "label": prediction.label,
            "confidence": float(prediction.confidence),
            "source": source,
            "theme": prediction.theme,
            "profile": payload,
            "sales_prediction_id": sale.id,
            "predicted_sales_millions": float(sale.predicted_sales_millions),
            "model_version": prediction.model_version,
        },
    )
    record_audit(
        "prediction.created",
        metadata={
            "input": payload,
            "source": "vision",
            "vision_prediction_id": prediction.id,
            "predicted_sales_millions": float(sale.predicted_sales_millions),
            "model_version": sale.model_version,
        },
    )
    db.session.commit()

    logger.info(
        "vision_prediction_created",
        extra={
            "vision_prediction_id": prediction.id,
            "sales_prediction_id": sale.id,
            "label": prediction.label,
            "theme": prediction.theme,
            "profile": payload,
            "predicted_sales_millions": float(sale.predicted_sales_millions),
        },
    )

    if _wants_json():
        return jsonify(_sales_response(prediction, sale))

    flash("Imagen clasificada y ventas estimadas correctamente.", "success")
    return redirect(url_for("vision.index", prediction_id=prediction.id))


@bp.route("/<int:prediction_id>/recalculate", methods=["POST"])
@login_required
def recalculate(prediction_id: int):
    vision = db.session.get(VisionPrediction, prediction_id)
    if vision is None or vision.user_id != current_user.id:
        abort(404)

    api = get_api_client()
    try:
        sales_info = api.model_info()
    except ApiError as exc:
        logger.error("sales_model_info_unavailable", extra={"error": str(exc)})
        abort(503)

    platforms = list(sales_info.get("allowed_platforms") or [])
    genres = list(sales_info.get("allowed_genres") or [])
    platform = (request.form.get("platform") or "").strip()
    genre = (request.form.get("genre") or "").strip()
    publisher = (request.form.get("publisher") or "Other").strip() or "Other"
    year = request.form.get("year", type=int)

    errors = []
    if platform not in platforms:
        errors.append("Selecciona una plataforma valida.")
    if genre not in genres:
        errors.append("Selecciona un genero valido.")
    if not publisher or len(publisher) > 120:
        errors.append("La editorial debe tener entre 1 y 120 caracteres.")
    if year is None or not 1970 <= year <= 2030:
        errors.append("El ano debe estar entre 1970 y 2030.")

    if errors:
        flash(" ".join(errors), "danger")
        return redirect(url_for("vision.index", prediction_id=vision.id))

    payload = {
        "platform": platform,
        "genre": genre,
        "publisher": publisher,
        "year": year,
    }

    try:
        sales_result = api.predict(payload)
    except ApiValidationError as exc:
        record_audit(
            "vision.prediction_recalculation_failed",
            status="failure",
            metadata={
                "vision_prediction_id": vision.id,
                "input": payload,
            },
            error=str(exc),
        )
        db.session.commit()
        flash(str(exc), "danger")
        return redirect(url_for("vision.index", prediction_id=vision.id))
    except ApiUnavailable as exc:
        record_audit(
            "vision.prediction_recalculation_failed",
            status="failure",
            metadata={
                "vision_prediction_id": vision.id,
                "input": payload,
            },
            error=str(exc),
        )
        db.session.commit()
        logger.error("sales_api_unavailable", extra={"error": str(exc)})
        abort(503)

    sale = vision.sales_prediction
    if sale is None:
        sale = Prediction(user_id=current_user.id)
        db.session.add(sale)
    _apply_sales_result(sale, payload, sales_result)
    db.session.flush()
    vision.prediction_id = sale.id

    record_audit(
        "vision.prediction.recalculated",
        metadata={
            "vision_prediction_id": vision.id,
            "sales_prediction_id": sale.id,
            "input": payload,
            "predicted_sales_millions": float(sale.predicted_sales_millions),
            "model_version": sale.model_version,
        },
    )
    db.session.commit()

    flash("Perfil actualizado y ventas recalculadas.", "success")
    return redirect(url_for("vision.index", prediction_id=vision.id))


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
    stmt = (
        stmt.options(selectinload(VisionPrediction.sales_prediction))
        .order_by(VisionPrediction.created_at.desc())
    )

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
