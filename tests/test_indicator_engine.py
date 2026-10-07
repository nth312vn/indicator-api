import pytest
from app.core.exceptions import InvalidIndicatorError
from app.schemas.indicator import IndicatorItem
from app.schemas.ohlcv import OHLCVRecord
from app.services.indicator_engine import (
    IndicatorEngine,
    normalize_talib_params,
    sanitize_value,
)
from app.services.mock_fiin_service import generate_mock_ohlcv


@pytest.fixture
def sample_records():
    response = generate_mock_ohlcv(tickers="AAPL", page_size=120)
    return response.data


@pytest.fixture
def engine():
    return IndicatorEngine(max_workers=4)


def test_param_normalization():
    norm_sma = normalize_talib_params("SMA", {"period": 20})
    assert norm_sma == {"timeperiod": 20}

    norm_macd = normalize_talib_params("MACD", {"fast_period": 10, "slow_period": 20, "signal_period": 7})
    assert norm_macd == {"fastperiod": 10, "slowperiod": 20, "signalperiod": 7}

    norm_bbands = normalize_talib_params("BBANDS", {"period": 15, "nb_dev_up": 2.5, "nb_dev_dn": 2.5})
    assert norm_bbands == {"timeperiod": 15, "nbdevup": 2.5, "nbdevdn": 2.5}


def test_sanitize_value():
    assert sanitize_value(float("nan")) is None
    assert sanitize_value(float("inf")) is None
    assert sanitize_value(172.56789) == 172.5679
    assert sanitize_value(None) is None


@pytest.mark.asyncio
async def test_single_sma_indicator(engine, sample_records):
    indicator = IndicatorItem(name="SMA", parameters={"period": 20})
    data_points, labels = await engine.calculate_indicators_for_records(
        records=sample_records,
        indicators=[indicator],
    )

    assert len(data_points) == len(sample_records)
    assert "SMA" in labels
    assert data_points[0].indicators["SMA"]["value"] is None
    assert data_points[0].indicators["SMA"]["params"] == {"period": 20}
    assert data_points[18].indicators["SMA"]["value"] is None
    assert data_points[19].indicators["SMA"]["value"] is not None
    assert isinstance(data_points[19].indicators["SMA"]["value"], float)
    # Check backward compatibility with indicator alias
    assert data_points[19].indicator["SMA"]["value"] is not None
    assert data_points[0].trading_date is not None


@pytest.mark.asyncio
async def test_multiple_indicators_parallel(engine, sample_records):
    indicators = [
        IndicatorItem(name="SMA", parameters={"period": 20}),
        IndicatorItem(name="EMA", parameters={"period": 30}),
        IndicatorItem(name="RSI", parameters={"period": 14}),
        IndicatorItem(name="MACD", parameters={"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}),
        IndicatorItem(name="BBANDS", parameters={"period": 20}),
    ]

    data_points, labels = await engine.calculate_indicators_for_records(
        records=sample_records,
        indicators=indicators,
    )

    assert len(data_points) == len(sample_records)
    last_point = data_points[-1]

    # Single-output indicators have float value
    assert last_point.indicators["SMA"]["value"] is not None
    assert isinstance(last_point.indicators["SMA"]["value"], float)
    assert last_point.indicators["SMA"]["params"] == {"period": 20}

    assert last_point.indicators["EMA"]["value"] is not None
    assert isinstance(last_point.indicators["EMA"]["value"], float)

    assert last_point.indicators["RSI"]["value"] is not None
    assert isinstance(last_point.indicators["RSI"]["value"], float)

    # Multi-output indicators have dict value
    assert last_point.indicators["MACD"]["value"]["macd"] is not None
    assert last_point.indicators["MACD"]["value"]["macdsignal"] is not None
    assert last_point.indicators["MACD"]["value"]["macdhist"] is not None
    assert last_point.indicators["MACD"]["params"] == {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}

    assert last_point.indicators["BBANDS"]["value"]["upperband"] is not None
    assert last_point.indicators["BBANDS"]["value"]["middleband"] is not None
    assert last_point.indicators["BBANDS"]["value"]["lowerband"] is not None


@pytest.mark.asyncio
async def test_custom_indicators_vwap_supertrend_ichimoku_keltner(engine, sample_records):
    custom_indicators = [
        IndicatorItem(name="VWAP"),
        IndicatorItem(name="SUPERTREND", parameters={"period": 10, "multiplier": 3.0}),
        IndicatorItem(name="ICHIMOKU"),
        IndicatorItem(name="KELTNER", parameters={"period": 20, "multiplier": 2.0}),
        IndicatorItem(name="PIVOT_POINTS"),
        IndicatorItem(name="HEIKIN_ASHI"),
    ]

    data_points, labels = await engine.calculate_indicators_for_records(
        records=sample_records,
        indicators=custom_indicators,
    )

    assert len(data_points) == len(sample_records)
    last_bar = data_points[-1]

    # Verify VWAP (single output)
    assert last_bar.indicators["VWAP"]["value"] is not None
    assert isinstance(last_bar.indicators["VWAP"]["value"], float)

    # Verify SuperTrend (multi output)
    assert last_bar.indicators["SUPERTREND"]["value"]["supertrend"] is not None
    assert last_bar.indicators["SUPERTREND"]["value"]["trend"] in (1.0, -1.0)
    assert last_bar.indicators["SUPERTREND"]["params"] == {"period": 10, "multiplier": 3.0}

    # Verify Ichimoku (multi output)
    assert last_bar.indicators["ICHIMOKU"]["value"]["tenkan_sen"] is not None
    assert last_bar.indicators["ICHIMOKU"]["value"]["kijun_sen"] is not None

    # Verify Keltner Channel (multi output)
    assert last_bar.indicators["KELTNER"]["value"]["upperband"] is not None

    # Verify Pivot Points (multi output)
    assert last_bar.indicators["PIVOT_POINTS"]["value"]["pivot"] is not None

    # Verify Heikin-Ashi (multi output)
    assert last_bar.indicators["HEIKIN_ASHI"]["value"]["ha_close"] is not None


@pytest.mark.asyncio
async def test_candlestick_pattern_aliases(engine, sample_records):
    pattern_indicators = [
        IndicatorItem(name="DOJI"),
        IndicatorItem(name="HAMMER"),
        IndicatorItem(name="ENGULFING"),
    ]

    data_points, labels = await engine.calculate_indicators_for_records(
        records=sample_records,
        indicators=pattern_indicators,
    )

    assert len(data_points) == len(sample_records)
    last_bar = data_points[-1]
    assert "DOJI" in last_bar.indicators
    assert "HAMMER" in last_bar.indicators
    assert "ENGULFING" in last_bar.indicators
    assert "value" in last_bar.indicators["DOJI"]
    assert "params" in last_bar.indicators["DOJI"]


@pytest.mark.asyncio
async def test_duplicate_indicator_disambiguation(engine, sample_records):
    indicators = [
        IndicatorItem(name="SMA", parameters={"period": 10}),
        IndicatorItem(name="SMA", parameters={"period": 20}),
    ]

    data_points, labels = await engine.calculate_indicators_for_records(
        records=sample_records,
        indicators=indicators,
    )

    assert len(data_points) == len(sample_records)
    last_bar = data_points[-1]
    assert "SMA_10" in last_bar.indicators
    assert "SMA_20" in last_bar.indicators
    assert last_bar.indicators["SMA_10"]["params"] == {"period": 10}
    assert last_bar.indicators["SMA_20"]["params"] == {"period": 20}


@pytest.mark.asyncio
async def test_invalid_indicator_raises_error(engine, sample_records):
    invalid_ind = IndicatorItem(name="NON_EXISTENT_INDICATOR", parameters={})
    with pytest.raises(InvalidIndicatorError) as exc_info:
        await engine.calculate_indicators_for_records(
            records=sample_records,
            indicators=[invalid_ind],
        )
    assert "is not supported" in str(exc_info.value)


@pytest.mark.asyncio
async def test_multiple_tickers(engine):
    resp = generate_mock_ohlcv(tickers="AAPL,MSFT", page_size=300)
    records = resp.data

    indicator = IndicatorItem(name="SMA", parameters={"period": 10})
    data_points, labels = await engine.calculate_indicators_for_records(
        records=records,
        indicators=[indicator],
    )

    tickers_in_output = {p.ticker for p in data_points}
    assert "AAPL" in tickers_in_output
    assert "MSFT" in tickers_in_output
    assert all(hasattr(p, "trading_date") for p in data_points)
    assert all(hasattr(p, "indicators") for p in data_points)
    assert all(hasattr(p, "indicator") for p in data_points)
