from fastapi import APIRouter
from app.api.v1.endpoints import fiin_mock, indicator

api_router = APIRouter()

# Technical Indicator calculation endpoints
api_router.include_router(indicator.router)

# Also alias plural /indicators to same router for user convenience
indicators_plural_router = APIRouter(prefix="/indicators", tags=["Indicators"])
indicators_plural_router.add_api_route(
    "/calculate",
    indicator.calculate_indicators,
    methods=["POST"],
    response_model=indicator.IndicatorCalculateResponse,
    summary="Calculate Technical Indicators (Plural alias)",
    include_in_schema=False,
)
indicators_plural_router.add_api_route(
    "/available",
    indicator.list_available_indicators,
    methods=["GET"],
    summary="List available indicators (Plural alias)",
    include_in_schema=False,
)
api_router.include_router(indicators_plural_router)

# Fiin OHLCV endpoint (Live/Mock)
api_router.include_router(fiin_mock.router)
