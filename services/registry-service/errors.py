"""Consistent problem responses for API and database failures."""

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError, TimeoutError
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

    @app.exception_handler(TimeoutError)
    @app.exception_handler(DBAPIError)
    async def handle_database_error(
        request: Request, error: DBAPIError | TimeoutError
    ) -> JSONResponse:
        if isinstance(error, IntegrityError):
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint == "uq_plots_farm_id_name":
                return problem_response(request, 409, "A plot with this name already exists in the farm.")
            if constraint == "fk_plots_farm_id" and request.method == "DELETE":
                return problem_response(request, 409, "Cannot delete a farm with plots.")
            if constraint in {"fk_plots_farm_id", "fk_plots_crop_id", "fk_plots_soil_id", "fk_plots_emitter_id"}:
                return problem_response(request, 422, f"{constraint.removeprefix('fk_plots_')} does not exist.")
        return problem_response(request, 503, "The registry database is unavailable.")
