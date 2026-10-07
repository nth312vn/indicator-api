from typing import Any, Callable, Dict, List, Tuple
import numpy as np
import talib.abstract as ta


def calc_vwap(inputs: Dict[str, np.ndarray], **kwargs) -> Dict[str, np.ndarray]:
    """
    Volume Weighted Average Price (VWAP).
    Computes cumulative (Typical Price * Volume) / Cumulative Volume.
    """
    high = inputs["high"]
    low = inputs["low"]
    close = inputs["close"]
    volume = inputs["volume"]

    typical_price = (high + low + close) / 3.0
    cum_pv = np.cumsum(typical_price * volume)
    cum_vol = np.cumsum(volume)

    vwap = np.where(cum_vol > 0, cum_pv / cum_vol, np.nan)
    return {"vwap": vwap}


def calc_supertrend(
    inputs: Dict[str, np.ndarray],
    period: int = 10,
    multiplier: float = 3.0,
    **kwargs,
) -> Dict[str, np.ndarray]:
    """
    SuperTrend indicator.
    Combines ATR with trailing bands to indicate trend direction and stop levels.
    Returns: supertrend line, trend direction (1 for Bullish, -1 for Bearish), upperband, lowerband.
    """
    high = inputs["high"]
    low = inputs["low"]
    close = inputs["close"]
    n = len(close)

    period = int(period)
    multiplier = float(multiplier)

    atr = ta.ATR(inputs, timeperiod=period)
    hl2 = (high + low) / 2.0
    upper_basic = hl2 + (multiplier * atr)
    lower_basic = hl2 - (multiplier * atr)

    upper_band = np.full(n, np.nan, dtype=np.float64)
    lower_band = np.full(n, np.nan, dtype=np.float64)
    trend = np.ones(n, dtype=np.float64)
    supertrend = np.full(n, np.nan, dtype=np.float64)

    valid_indices = np.where(~np.isnan(atr))[0]
    if len(valid_indices) == 0:
        return {
            "supertrend": supertrend,
            "trend": trend,
            "upperband": upper_band,
            "lowerband": lower_band,
        }

    first_idx = valid_indices[0]
    upper_band[first_idx] = upper_basic[first_idx]
    lower_band[first_idx] = lower_basic[first_idx]
    supertrend[first_idx] = lower_band[first_idx]
    trend[first_idx] = 1.0

    for i in range(first_idx + 1, n):
        # Trailing lower band
        if lower_basic[i] > lower_band[i - 1] or close[i - 1] < lower_band[i - 1]:
            lower_band[i] = lower_basic[i]
        else:
            lower_band[i] = lower_band[i - 1]

        # Trailing upper band
        if upper_basic[i] < upper_band[i - 1] or close[i - 1] > upper_band[i - 1]:
            upper_band[i] = upper_basic[i]
        else:
            upper_band[i] = upper_band[i - 1]

        # Determine trend direction
        prev_trend = trend[i - 1]
        if prev_trend == 1.0:
            if close[i] < lower_band[i]:
                trend[i] = -1.0
                supertrend[i] = upper_band[i]
            else:
                trend[i] = 1.0
                supertrend[i] = lower_band[i]
        else:
            if close[i] > upper_band[i]:
                trend[i] = 1.0
                supertrend[i] = lower_band[i]
            else:
                trend[i] = -1.0
                supertrend[i] = upper_band[i]

    return {
        "supertrend": supertrend,
        "trend": trend,
        "upperband": upper_band,
        "lowerband": lower_band,
    }


def calc_ichimoku(
    inputs: Dict[str, np.ndarray],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    **kwargs,
) -> Dict[str, np.ndarray]:
    """
    Ichimoku Kinko Hyo (Ichimoku Cloud).
    Returns: tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b.
    """
    high = inputs["high"]
    low = inputs["low"]
    n = len(high)

    tenkan_period = int(tenkan_period)
    kijun_period = int(kijun_period)
    senkou_b_period = int(senkou_b_period)

    def donchian_midpoint(h: np.ndarray, l: np.ndarray, p: int) -> np.ndarray:
        res = np.full(n, np.nan, dtype=np.float64)
        for i in range(p - 1, n):
            res[i] = (np.max(h[i - p + 1 : i + 1]) + np.min(l[i - p + 1 : i + 1])) / 2.0
        return res

    tenkan = donchian_midpoint(high, low, tenkan_period)
    kijun = donchian_midpoint(high, low, kijun_period)
    senkou_a = (tenkan + kijun) / 2.0
    senkou_b = donchian_midpoint(high, low, senkou_b_period)

    return {
        "tenkan_sen": tenkan,
        "kijun_sen": kijun,
        "senkou_span_a": senkou_a,
        "senkou_span_b": senkou_b,
    }


def calc_keltner(
    inputs: Dict[str, np.ndarray],
    period: int = 20,
    multiplier: float = 2.0,
    atr_period: int = 10,
    **kwargs,
) -> Dict[str, np.ndarray]:
    """
    Keltner Channel.
    Returns: upperband, middleband, lowerband.
    """
    period = int(period)
    multiplier = float(multiplier)
    atr_period = int(atr_period)

    middle = ta.EMA(inputs, timeperiod=period)
    atr = ta.ATR(inputs, timeperiod=atr_period)
    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)

    return {
        "upperband": upper,
        "middleband": middle,
        "lowerband": lower,
    }


def calc_pivot_points(inputs: Dict[str, np.ndarray], **kwargs) -> Dict[str, np.ndarray]:
    """
    Classic & Fibonacci Pivot Points based on previous bar HLC.
    Returns: pivot (P), r1, r2, r3, s1, s2, s3, fib_r1, fib_s1.
    """
    high = inputs["high"]
    low = inputs["low"]
    close = inputs["close"]
    n = len(close)

    p = np.full(n, np.nan, dtype=np.float64)
    r1 = np.full(n, np.nan, dtype=np.float64)
    r2 = np.full(n, np.nan, dtype=np.float64)
    r3 = np.full(n, np.nan, dtype=np.float64)
    s1 = np.full(n, np.nan, dtype=np.float64)
    s2 = np.full(n, np.nan, dtype=np.float64)
    s3 = np.full(n, np.nan, dtype=np.float64)

    for i in range(1, n):
        prev_h, prev_l, prev_c = high[i - 1], low[i - 1], close[i - 1]
        rng = prev_h - prev_l
        pivot = (prev_h + prev_l + prev_c) / 3.0
        p[i] = pivot
        r1[i] = (2.0 * pivot) - prev_l
        s1[i] = (2.0 * pivot) - prev_h
        r2[i] = pivot + rng
        s2[i] = pivot - rng
        r3[i] = prev_h + (2.0 * (pivot - prev_l))
        s3[i] = prev_l - (2.0 * (prev_h - pivot))

    return {
        "pivot": p,
        "r1": r1,
        "r2": r2,
        "r3": r3,
        "s1": s1,
        "s2": s2,
        "s3": s3,
    }


def calc_heikin_ashi(inputs: Dict[str, np.ndarray], **kwargs) -> Dict[str, np.ndarray]:
    """
    Heikin-Ashi candlestick smoothing transform.
    Returns: ha_open, ha_high, ha_low, ha_close.
    """
    open_p = inputs["open"]
    high = inputs["high"]
    low = inputs["low"]
    close = inputs["close"]
    n = len(close)

    ha_close = (open_p + high + low + close) / 4.0
    ha_open = np.full(n, np.nan, dtype=np.float64)
    ha_high = np.full(n, np.nan, dtype=np.float64)
    ha_low = np.full(n, np.nan, dtype=np.float64)

    if n > 0:
        ha_open[0] = (open_p[0] + close[0]) / 2.0
        ha_high[0] = high[0]
        ha_low[0] = low[0]
        for i in range(1, n):
            ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
            ha_high[i] = max(high[i], ha_open[i], ha_close[i])
            ha_low[i] = min(low[i], ha_open[i], ha_close[i])

    return {
        "ha_open": ha_open,
        "ha_high": ha_high,
        "ha_low": ha_low,
        "ha_close": ha_close,
    }


# Registry of custom indicators metadata and functions
CUSTOM_INDICATORS: Dict[str, Dict[str, Any]] = {
    "VWAP": {
        "name": "VWAP",
        "display_name": "Volume Weighted Average Price",
        "group": "Volume / Price",
        "func": calc_vwap,
        "parameters": {},
        "output_names": ["vwap"],
    },
    "SUPERTREND": {
        "name": "SUPERTREND",
        "display_name": "SuperTrend",
        "group": "Trend / Volatility",
        "func": calc_supertrend,
        "parameters": {"period": 10, "multiplier": 3.0},
        "output_names": ["supertrend", "trend", "upperband", "lowerband"],
    },
    "ICHIMOKU": {
        "name": "ICHIMOKU",
        "display_name": "Ichimoku Kinko Hyo (Cloud)",
        "group": "Trend / Momentum",
        "func": calc_ichimoku,
        "parameters": {"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52},
        "output_names": ["tenkan_sen", "kijun_sen", "senkou_span_a", "senkou_span_b"],
    },
    "KELTNER": {
        "name": "KELTNER",
        "display_name": "Keltner Channel",
        "group": "Volatility / Overlap",
        "func": calc_keltner,
        "parameters": {"period": 20, "multiplier": 2.0, "atr_period": 10},
        "output_names": ["upperband", "middleband", "lowerband"],
    },
    "PIVOT_POINTS": {
        "name": "PIVOT_POINTS",
        "display_name": "Classic Pivot Points",
        "group": "Support / Resistance",
        "func": calc_pivot_points,
        "parameters": {},
        "output_names": ["pivot", "r1", "r2", "r3", "s1", "s2", "s3"],
    },
    "HEIKIN_ASHI": {
        "name": "HEIKIN_ASHI",
        "display_name": "Heikin-Ashi Smoothed Candlestick",
        "group": "Price Transform",
        "func": calc_heikin_ashi,
        "parameters": {},
        "output_names": ["ha_open", "ha_high", "ha_low", "ha_close"],
    },
}

# User-friendly aliases
INDICATOR_ALIASES: Dict[str, str] = {
    # Custom aliases
    "SUPER_TREND": "SUPERTREND",
    "KC": "KELTNER",
    "PIVOT": "PIVOT_POINTS",
    "PIVOTS": "PIVOT_POINTS",
    "HA": "HEIKIN_ASHI",
    # Candlestick pattern aliases
    "DOJI": "CDLDOJI",
    "HAMMER": "CDLHAMMER",
    "ENGULFING": "CDLENGULFING",
    "MORNING_STAR": "CDLMORNINGSTAR",
    "EVENING_STAR": "CDLEVENINGSTAR",
    "SHOOTING_STAR": "CDLSHOOTINGSTAR",
    "HANGING_MAN": "CDLHANGINGMAN",
    "HARAMI": "CDLHARAMI",
    "MARUBOZU": "CDLMARUBOZU",
    "INVERTED_HAMMER": "CDLINVERTEDHAMMER",
    "SPINNING_TOP": "CDLSPINNINGTOP",
    "THREE_WHITE_SOLDIERS": "CDL3WHITESOLDIERS",
    "THREE_BLACK_CROWS": "CDL3BLACKCROWS",
    "DRAGONFLY_DOJI": "CDLDRAGONFLYDOJI",
    "GRAVESTONE_DOJI": "CDLGRAVESTONEDOJI",
    "BELTHOLD": "CDLBELTHOLD",
    "PIERCING": "CDLPIERCING",
    "DARK_CLOUD": "CDLDARKCLOUDCOVER",
}
