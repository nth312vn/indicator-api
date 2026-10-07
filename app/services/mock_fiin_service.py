import math
import random
from datetime import date, datetime, timedelta
from typing import List, Optional
from app.schemas.ohlcv import FiinOHLCVResponse, OHLCVRecord, PaginationMetadata


def generate_mock_ohlcv(
    tickers: List[str] | str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> FiinOHLCVResponse:
    """
    Generate realistic synthetic OHLCV data for testing and local development.
    Guarantees chronological data with realistic price movements.
    """
    if isinstance(tickers, str):
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    else:
        ticker_list = [t.strip().upper() for t in tickers if t.strip()]

    if not ticker_list:
        ticker_list = ["AAPL"]

    # Parse or default date range (default last 120 days to ensure enough bars for SMA 20/50)
    end_dt = datetime.strptime(end_time, "%Y-%m-%d").date() if end_time else date.today()
    start_dt = datetime.strptime(start_time, "%Y-%m-%d").date() if start_time else (end_dt - timedelta(days=150))

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    # Generate business days (exclude Saturday & Sunday)
    trade_dates: List[str] = []
    curr = start_dt
    while curr <= end_dt:
        if curr.weekday() < 5:  # Monday to Friday
            trade_dates.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)

    all_records: List[OHLCVRecord] = []

    # Deterministic seed based on ticker name for consistent test reproducibility
    for t_idx, ticker in enumerate(ticker_list):
        rng = random.Random(hash(ticker) & 0xFFFFFFFF)
        base_price = 150.0 + (t_idx * 25.0)
        curr_price = base_price

        for i, dt_str in enumerate(trade_dates):
            # Drift and volatility
            daily_return = rng.gauss(0.0005, 0.015)
            open_price = round(curr_price * (1 + rng.uniform(-0.005, 0.005)), 2)
            close_price = round(open_price * (1 + daily_return), 2)
            high_price = round(max(open_price, close_price) * (1 + abs(rng.gauss(0, 0.008))), 2)
            low_price = round(min(open_price, close_price) * (1 - abs(rng.gauss(0, 0.008))), 2)
            volume = float(rng.randint(1_000_000, 25_000_000))

            all_records.append(
                OHLCVRecord(
                    ticker=ticker,
                    trade_date=dt_str,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                )
            )
            curr_price = close_price

    total_records = len(all_records)
    total_pages = max(1, math.ceil(total_records / page_size)) if page_size > 0 else 1

    # Apply pagination slice
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_records = all_records[start_idx:end_idx] if start_idx < total_records else []

    return FiinOHLCVResponse(
        status="success",
        data=paginated_records,
        pagination=PaginationMetadata(
            page=page,
            total_pages=total_pages,
            page_size=page_size,
            total_records=total_records,
        ),
    )
