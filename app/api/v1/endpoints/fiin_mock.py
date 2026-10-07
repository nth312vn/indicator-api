from typing import List, Optional
from fastapi import APIRouter, Query, status
from app.schemas.ohlcv import FiinOHLCVResponse
from app.services.mock_fiin_service import generate_mock_ohlcv

router = APIRouter(prefix="/portfolio-construction/fiin_data", tags=["Fiin Data (OHLCV)"])


@router.get(
    "/stockist",
    response_model=FiinOHLCVResponse,
    status_code=status.HTTP_200_OK,
    summary="Get OHLCV stock data (Upstream Fiin API / Mock)",
    description="Endpoint serving OHLCV data matching Fiin Data specification for stockist.",
)
async def get_stockist_ohlcv(
    ticker: List[str] = Query(..., description="Mã cổ phiếu (có thể truyền nhiều mã: ticker=AAPL,MSFT hoặc ticker=AAPL&ticker=MSFT)"),
    start_time: Optional[str] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    end_time: Optional[str] = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Trang dữ liệu"),
    page_size: int = Query(100, ge=1, le=50000, description="Kích thước trang"),
) -> FiinOHLCVResponse:
    """Generate or retrieve stockist OHLCV data."""
    ticker_list: List[str] = []
    for t in ticker:
        ticker_list.extend(t.split(","))
    ticker_clean = [x.strip().upper() for x in ticker_list if x.strip()]

    return generate_mock_ohlcv(
        tickers=ticker_clean,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
