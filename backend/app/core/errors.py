"""Reusable HTTP error helpers with structured error bodies."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str, **detail: Any) -> HTTPException:
    body: dict[str, Any] = {"code": code, "message": message}
    body.update(detail)
    return HTTPException(status_code=status_code, detail=body)


def not_found(resource: str, identifier: str) -> HTTPException:
    return api_error(
        404,
        "NOT_FOUND",
        f"{resource} '{identifier}' could not be found.",
        resource=resource,
        identifier=identifier,
    )


def conflict(resource: str, message: str) -> HTTPException:
    return api_error(409, "CONFLICT", message, resource=resource)


def validation_error(message: str) -> HTTPException:
    return api_error(422, "VALIDATION_ERROR", message)