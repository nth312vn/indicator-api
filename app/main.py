from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
import httpx

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger
from app.services import fiin_client, indicator_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for resource initialization and teardown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")

    # Initialize shared HTTP client with connection pooling
    http_client = httpx.AsyncClient(
        base_url=settings.FIIN_DATA_API_BASE_URL.rstrip("/"),
        timeout=httpx.Timeout(settings.FIIN_API_TIMEOUT_SECONDS, connect=5.0),
        limits=httpx.Limits(
            max_keepalive_connections=settings.FIIN_MAX_KEEPALIVE_CONNECTIONS,
            max_connections=settings.FIIN_MAX_CONNECTIONS,
        ),
    )
    fiin_client._fiin_client_instance = fiin_client.FiinDataClient(client=http_client)

    yield

    # Clean teardown
    logger.info("Shutting down application resources...")
    await http_client.aclose()
    indicator_engine.get_indicator_engine().shutdown()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="High-performance FastAPI service for calculating Technical Indicators via TA-Lib on OHLCV market data.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers
register_exception_handlers(app)

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", status_code=status.HTTP_200_OK, include_in_schema=False)
async def root():
    """Root endpoint redirecting attention to API documentation."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs_url": "/docs",
        "health_url": "/health",
        "calculate_endpoint": f"{settings.API_V1_PREFIX}/indicator/calculate",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
