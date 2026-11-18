"""Pruebas del formateador JSON y de la redaccion de datos sensibles."""

import json
import logging

from app.logging_config import (
    JsonFormatter,
    RequestContextFilter,
    SensitiveDataFilter,
    redact,
    request_id_var,
    user_id_var,
)


def test_redact_removes_sensitive_values():
    text = "password=secreto Authorization: Bearer abc123 token: xyz"

    cleaned = redact(text)

    assert "secreto" not in cleaned
    assert "abc123" not in cleaned
    assert "xyz" not in cleaned
    assert "***" in cleaned


def test_json_formatter_includes_request_context():
    request_id_var.set("req-123")
    user_id_var.set(7)
    try:
        record = logging.LogRecord(
            "app.test",
            logging.INFO,
            __file__,
            1,
            "hola %s",
            ("mundo",),
            None,
        )
        RequestContextFilter().filter(record)
        SensitiveDataFilter().filter(record)

        payload = json.loads(JsonFormatter().format(record))

        assert payload["level"] == "INFO"
        assert payload["logger"] == "app.test"
        assert payload["message"] == "hola mundo"
        assert payload["request_id"] == "req-123"
        assert payload["user_id"] == 7
    finally:
        request_id_var.set(None)
        user_id_var.set(None)


def test_sensitive_filter_scrubs_message():
    record = logging.LogRecord(
        "app.test", logging.INFO, __file__, 1, "password=secreto", None, None
    )

    SensitiveDataFilter().filter(record)
    payload = json.loads(JsonFormatter().format(record))

    assert "secreto" not in payload["message"]
