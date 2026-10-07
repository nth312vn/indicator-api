import time
import pytest
from app.schemas.indicator import IndicatorItem
from app.services.indicator_engine import IndicatorEngine
from app.services.mock_fiin_service import generate_mock_ohlcv


@pytest.mark.asyncio
async def test_parallel_indicators_performance():
    # 500 bars of historical data
    ohlcv = generate_mock_ohlcv(tickers="AAPL", page_size=500)
    records = ohlcv.data

    # A list of 12 distinct indicators
    indicators = [
        IndicatorItem(name="SMA", parameters={"period": 20}),
        IndicatorItem(name="SMA", parameters={"period": 50}),
        IndicatorItem(name="SMA", parameters={"period": 200}),
        IndicatorItem(name="EMA", parameters={"period": 20}),
        IndicatorItem(name="EMA", parameters={"period": 50}),
        IndicatorItem(name="RSI", parameters={"period": 14}),
        IndicatorItem(name="MACD", parameters={"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}),
        IndicatorItem(name="BBANDS", parameters={"period": 20}),
        IndicatorItem(name="ATR", parameters={"period": 14}),
        IndicatorItem(name="STOCH", parameters={"fastk_period": 14, "slowk_period": 3, "slowd_period": 3}),
        IndicatorItem(name="CCI", parameters={"period": 14}),
        IndicatorItem(name="WILLR", parameters={"period": 14}),
    ]

    engine = IndicatorEngine(max_workers=8)

    t0 = time.perf_counter()
    data_points, labels = await engine.calculate_indicators_for_records(
        records=records,
        indicators=indicators,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"\nCalculated {len(indicators)} indicators on {len(records)} bars in {elapsed_ms:.2f} ms")

    assert len(data_points) == len(records)
    # TA-Lib in C + ThreadPoolExecutor should easily compute 12 indicators on 500 bars in under 100ms
    assert elapsed_ms < 500.0
    assert len(labels) == len(indicators)
