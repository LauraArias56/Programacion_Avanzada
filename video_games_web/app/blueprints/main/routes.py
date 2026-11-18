"""Rutas principales: dashboard, prediccion e historial."""

import csv
import io
import logging
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ...extensions import db
from ...forms.predict_form import PredictForm
from ...models import Prediction
from ...services.api_client import (
    ApiError,
    ApiUnavailable,
    ApiValidationError,
    get_api_client,
)
from ...services.audit import record_audit

bp = Blueprint("main", __name__)
logger = logging.getLogger("app.predict")


def safe_next_url(target: str | None) -> str | None:
    """Solo permite redirecciones internas."""
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/"):
        return None
    return target


def _prediction_payload(form: PredictForm) -> dict:
    return {
        "platform": form.platform.data,
        "genre": form.genre.data,
        "publisher": (form.publisher.data or "Other").strip() or "Other",
        "year": int(form.year.data),
    }


def _apply_choices(form: PredictForm, info: dict) -> None:
    form.platform.choices = [
        (value, value) for value in info.get("allowed_platforms", [])
    ]
    form.genre.choices = [(value, value) for value in info.get("allowed_genres", [])]


@bp.route("/")
def index():
    api = get_api_client()
    health = None
    info = None
    try:
        health = api.health()
    except ApiError as exc:
        logger.warning("api_health_unavailable", extra={"error": str(exc)})
    try:
        info = api.model_info()
    except ApiError as exc:
        logger.warning("api_model_info_unavailable", extra={"error": str(exc)})

    recent = []
    if current_user.is_authenticated:
        recent = db.session.scalars(
            db.select(Prediction)
            .where(Prediction.user_id == current_user.id)
            .order_by(Prediction.created_at.desc())
            .limit(5)
        ).all()

    return render_template(
        "main/index.html", health=health, info=info, recent=recent
    )


@bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    api = get_api_client()
    try:
        info = api.model_info()
    except ApiError:
        abort(503)

    form = PredictForm()
    _apply_choices(form, info)

    if form.validate_on_submit():
        payload = _prediction_payload(form)
        try:
            result = api.predict(payload)
        except ApiValidationError as exc:
            record_audit(
                "prediction.failed",
                status="failure",
                metadata={"input": payload},
                error=str(exc),
            )
            db.session.commit()
            logger.warning(
                "prediction_rejected",
                extra={"error": str(exc), "status": exc.status_code or 422},
            )
            flash(str(exc), "danger")
            return render_template(
                "main/predict.html", form=form, info=info
            )
        except ApiUnavailable as exc:
            record_audit(
                "prediction.failed",
                status="failure",
                metadata={"input": payload},
                error=str(exc),
            )
            db.session.commit()
            logger.error("prediction_api_unavailable", extra={"error": str(exc)})
            abort(503)

        prediction_data = result.get("prediction", {}) or {}
        interval = prediction_data.get("interval_95_millions") or [None, None]
        model_version = result.get("model_version") or info.get("model_version", "")

        prediction = Prediction(
            user_id=current_user.id,
            platform=payload["platform"],
            genre=payload["genre"],
            publisher=payload["publisher"],
            year=payload["year"],
            predicted_sales_millions=prediction_data.get("predicted_sales_millions", 0),
            predicted_log_sales=prediction_data.get("predicted_log_sales", 0),
            interval_low=interval[0],
            interval_high=interval[1] if len(interval) > 1 else None,
            warnings=prediction_data.get("warnings", []),
            model_version=model_version,
            request_id=getattr(g, "request_id", None),
        )
        db.session.add(prediction)
        record_audit(
            "prediction.created",
            metadata={
                "input": payload,
                "predicted_sales_millions": prediction_data.get(
                    "predicted_sales_millions"
                ),
                "model_version": model_version,
            },
        )
        db.session.commit()
        logger.info(
            "prediction_created",
            extra={
                "prediction_id": prediction.id,
                "model_version": model_version,
            },
        )
        flash("Prediccion generada correctamente.", "success")
        return redirect(
            url_for("main.prediction_detail", prediction_id=prediction.id)
        )

    return render_template("main/predict.html", form=form, info=info)


@bp.route("/history")
@login_required
def history():
    api = get_api_client()
    try:
        info = api.model_info()
    except ApiError:
        info = {"allowed_platforms": [], "allowed_genres": []}

    page = request.args.get("page", 1, type=int)
    platform = request.args.get("platform", "").strip()
    genre = request.args.get("genre", "").strip()
    year = request.args.get("year", type=int)

    stmt = db.select(Prediction).where(Prediction.user_id == current_user.id)
    if platform:
        stmt = stmt.where(Prediction.platform == platform)
    if genre:
        stmt = stmt.where(Prediction.genre == genre)
    if year:
        stmt = stmt.where(Prediction.year == year)
    stmt = stmt.order_by(Prediction.created_at.desc())

    pagination = db.paginate(
        stmt,
        page=max(page, 1),
        per_page=current_app.config["HISTORY_PAGE_SIZE"],
        error_out=False,
    )

    return render_template(
        "main/history.html",
        pagination=pagination,
        predictions=pagination.items,
        info=info,
        filters={"platform": platform, "genre": genre, "year": year},
    )


@bp.route("/history/<int:prediction_id>")
@login_required
def prediction_detail(prediction_id: int):
    prediction = db.session.get(Prediction, prediction_id)
    if prediction is None or prediction.user_id != current_user.id:
        abort(404)
    return render_template("main/detail.html", prediction=prediction)


@bp.route("/history/export.csv")
@login_required
def export_history():
    rows = db.session.scalars(
        db.select(Prediction)
        .where(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "fecha",
            "plataforma",
            "genero",
            "editorial",
            "ano",
            "ventas_millones",
            "log_ventas",
            "ic95_inferior",
            "ic95_superior",
            "model_version",
            "request_id",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.created_at.isoformat() if row.created_at else "",
                row.platform,
                row.genre,
                row.publisher,
                row.year,
                row.predicted_sales_millions,
                row.predicted_log_sales,
                row.interval_low,
                row.interval_high,
                row.model_version,
                row.request_id or "",
            ]
        )

    response = Response(buffer.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=historial.csv"
    return response
