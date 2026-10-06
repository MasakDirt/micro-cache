import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.exceptions import (
    PayloadNotFoundError,
    PayloadTooLargeError,
    StorageError,
    TransformerError,
)
from core.schemas import ErrorResponse

logger = logging.getLogger(__name__)

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PayloadNotFoundError, _domain_handler(404, logging.WARNING))
    app.add_exception_handler(PayloadTooLargeError, _domain_handler(413, logging.WARNING))
    app.add_exception_handler(TransformerError, _domain_handler(502, logging.ERROR))
    app.add_exception_handler(StorageError, _domain_handler(503, logging.ERROR))
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _unexpected_handler)


def _domain_handler(status: int, level: int) -> Handler:
    async def handle(request: Request, error: Exception) -> JSONResponse:
        _log(level, request, status, str(error), None)
        return _response(status, str(error))

    return handle


async def _validation_handler(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    detail = "; ".join(_describe(item) for item in error.errors())
    _log(logging.INFO, request, 422, detail, None)
    return _response(422, detail)


async def _unexpected_handler(request: Request, error: Exception) -> JSONResponse:
    _log(logging.ERROR, request, 500, repr(error), error)
    return _response(500, "Internal error")


def _describe(item: dict[str, object]) -> str:
    location = ".".join(str(part) for part in item["loc"][1:]) or str(item["loc"][0])  # type: ignore[index]
    message = str(item["msg"]).removeprefix("Value error, ")
    return f"{location}: {message}"


def _log(level: int, request: Request, status: int, detail: str, error: Exception | None) -> None:
    logger.log(
        level, "%s %s -> %s: %s", request.method, request.url.path, status, detail, exc_info=error
    )


def _response(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content=ErrorResponse(detail=detail).model_dump())
