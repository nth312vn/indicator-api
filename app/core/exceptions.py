from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.core.logging import logger


class IndicatorAppException(Exception):
    """Base exception for application."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class FiinDataFetchError(IndicatorAppException):
    """Raised when fetching OHLCV data from Fiin API fails."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY, details=details)


class InvalidIndicatorError(IndicatorAppException):
    """Raised when an invalid indicator name or invalid parameter is provided."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=422, details=details)


class InsufficientDataError(IndicatorAppException):
    """Raised when insufficient data points are available for calculation."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with FastAPI application."""

    @app.exception_handler(IndicatorAppException)
    async def app_exception_handler(request: Request, exc: IndicatorAppException):
        logger.warning(f"Handled application exception on {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception on {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error occurred while processing the request.",
                "details": str(exc) if get_settings().DEBUG else None,
            },
        )
