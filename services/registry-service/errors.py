"""Consistent problem responses for API and database failures."""

import sqlite3
from sqlalchemy.exc import SQLAlchemyError
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


ERROR_CODES = {
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION",
    503: "UNAVAILABLE",
}


def problem_response(
    request: Request,
    status: int,
    detail: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    response_headers = dict(headers or {})
    if status == 503:
        response_headers.setdefault("Retry-After", "5")
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        headers=response_headers,
        content={
            "type": "about:blank",
            "title": HTTPStatus(status).phrase,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "code": ERROR_CODES.get(status, "HTTP_ERROR"),
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
        return problem_response(request, error.status_code, str(error.detail), error.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        return problem_response(request, 422, detail)

    @app.exception_handler(SQLAlchemyError)
    @app.exception_handler(sqlite3.DatabaseError)
    async def handle_database_error(
        request: Request, error: sqlite3.DatabaseError
    ) -> JSONResponse:
        return problem_response(request, 503, "The registry database is unavailable.")
