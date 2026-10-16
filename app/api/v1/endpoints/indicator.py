from datetime import datetime, timedelta
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.core.exceptions import InvalidIndicatorError
from app.core.logging import logger
from app.schemas.indicator import IndicatorCalculateRequest, IndicatorCalculateResponse, IndicatorItem
from app.services.fiin_client import FiinDataClient, get_fiin_client
from app.services.indicator_engine import IndicatorEngine, get_indicator_engine

router = APIRouter(prefix="/indicator", tags=["Indicators"])


def get_lookback_days(indicators: List[IndicatorItem]) -> int:
    """Calculate required lookback days to fully warm up indicators before start_date."""
    max_period = 30
    for ind in indicators:
        for k, v in ind.parameters.items():
            if any(term in k.lower() for term in ("period", "length", "window")):
                try:
                    max_period = max(max_period, int(v))
                except (ValueError, TypeError):
                    pass
    # Multiply by ~2.0 calendar days per bar plus safety buffer (min 90 days)
    return max(int(max_period * 2.0), 90)


def has_valid_indicator_values(indicator_dict: Dict[str, Any]) -> bool:
    """Check if indicator dict contains at least one non-null value."""
    if not indicator_dict:
        return True
    for item in indicator_dict.values():
        if item is None:
            continue
        if isinstance(item, dict) and "value" in item:
            val = item["value"]
            if val is not None:
                if isinstance(val, dict):
                    if any(sub_v is not None for sub_v in val.values()):
                        return True
                else:
                    return True
        elif isinstance(item, dict):
            if any(sub_v is not None for sub_v in item.values()):
                return True
        else:
            return True
    return False


@router.get(
    "/available",
    status_code=status.HTTP_200_OK,
    summary="List all available Technical Indicators and parameters",
    description="Returns full metadata of 200+ indicators supported categorized with parameters.",
)
async def list_available_indicators(
    indicator_engine: IndicatorEngine = Depends(get_indicator_engine),
) -> Dict[str, Any]:
    """Retrieve full catalog of available indicators, groups, aliases, and parameter schemas."""
    return indicator_engine.get_available_indicators()


@router.post(
    "/calculate",
    response_model=IndicatorCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Technical Indicators for OHLCV data",
    description="Fetches OHLCV data and calculates technical indicators using TA-Lib and custom engines with lookback warming, multi-ticker support, and configurable sorting.",
)
async def calculate_indicators(
    body: IndicatorCalculateRequest,
    ticker: List[str] = Query(
        ...,
        description="Mã cổ phiếu, có thể truyền nhiều mã: ticker=AAPL,MSFT hoặc lặp ?ticker=AAPL&ticker=MSFT",
        examples=["AAPL", "AAPL,MSFT"],
    ),
    start_date: Optional[str] = Query(
        None,
        description="Ngày bắt đầu (định dạng YYYY-MM-DD)",
        examples=["2024-01-01"],
    ),
    end_date: Optional[str] = Query(
        None,
        description="Ngày kết thúc (định dạng YYYY-MM-DD)",
        examples=["2024-06-01"],
    ),
    page: int = Query(1, ge=1, description="Số trang phân trang"),
    page_size: int = Query(100, ge=1, le=5000, description="Số lượng bản ghi trên một trang"),
    sort: str = Query(
        "desc",
        description="Thứ tự sắp xếp theo ngày: 'desc' (mới nhất trước - chuẩn thị trường) hoặc 'asc' (cũ nhất trước)",
        pattern="^(desc|asc|DESC|ASC)$",
    ),
    drop_warmup: bool = Query(
        True,
        description="Tự động loại bỏ các nến khởi động (warm-up) chưa đủ dữ liệu tính toán và có giá trị null",
    ),
    flatten_output: Optional[bool] = Query(
        None,
        description="Định dạng hiển thị cho các chỉ báo nhiều đường (như MACD, BBANDS, STOCH): false = Nested Object gọn gàng, true = Flat keys, null = Bao gồm cả hai",
    ),
    fiin_client: FiinDataClient = Depends(get_fiin_client),
    indicator_engine: IndicatorEngine = Depends(get_indicator_engine),
) -> IndicatorCalculateResponse:
    # 1. Parse and clean tickers (supports both comma-separated and repeated params)
    parsed_tickers: List[str] = []
    for item in ticker:
        parsed_tickers.extend(item.split(","))
    clean_tickers = [t.strip().upper() for t in parsed_tickers if t.strip()]

    if not clean_tickers:
        raise InvalidIndicatorError("Tham số ticker không được để trống.")

    tickers_query_str = ",".join(clean_tickers)
    indicator_items = body.indicator_list

    # 2. Lookback buffer logic to eliminate nulls on requested start_date
    lookback_days = get_lookback_days(indicator_items)
    fetch_start_time = start_date
    if start_date:
        try:
            req_start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            fetch_start_time = (req_start_dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        except ValueError:
            fetch_start_time = start_date

    # 3. Fetch OHLCV historical data across all pages with lookback history
    ohlcv_response = await fiin_client.fetch_all_ohlcv(
        ticker=tickers_query_str,
        start_time=fetch_start_time,
        end_time=end_date,
    )

    records = ohlcv_response.data
    logger.info(f"Received {len(records)} OHLCV records for tickers={clean_tickers} (lookback from {fetch_start_time})")

    # 4. Calculate indicators concurrently using TA-Lib and custom engines
    all_calculated_data, _ = await indicator_engine.calculate_indicators_for_records(
        records=records,
        indicators=indicator_items,
    )

    # 5. Filter out lookback buffer bars if user specified start_date
    if start_date:
        all_calculated_data = [p for p in all_calculated_data if p.trading_date >= start_date]

    # 6. Drop warm-up bars where indicators are all null
    if drop_warmup:
        all_calculated_data = [p for p in all_calculated_data if has_valid_indicator_values(p.indicators)]

    # 7. Sort according to specified order (DESC = newest first, ASC = oldest first)
    is_desc = sort.lower() == "desc"
    all_calculated_data.sort(key=lambda x: (x.trading_date, x.ticker), reverse=is_desc)

    # 8. Optionally flatten multi-output indicators if requested
    if flatten_output is True:
        for p in all_calculated_data:
            flattened = {}
            for k, ind_data in p.indicators.items():
                if isinstance(ind_data, dict) and isinstance(ind_data.get("value"), dict):
                    for sub_k, sub_v in ind_data["value"].items():
                        flattened[f"{k}_{sub_k}"] = {
                            "params": ind_data.get("params", {}),
                            "value": sub_v,
                        }
                else:
                    flattened[k] = ind_data
            p.indicators = flattened
            p.indicator = flattened

    # 9. Apply pagination slicing
    total_record = len(all_calculated_data)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_data = all_calculated_data[start_idx:end_idx] if start_idx < total_record else []

    return IndicatorCalculateResponse(
        page=page,
        page_size=page_size,
        total_record=total_record,
        data=paginated_data,
    )
