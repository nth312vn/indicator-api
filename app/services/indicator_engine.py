import asyncio
from concurrent.futures import ThreadPoolExecutor
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import talib
import talib.abstract as ta

from app.core.config import get_settings
from app.core.exceptions import InvalidIndicatorError
from app.core.logging import logger
from app.schemas.indicator import CalculatedDataPoint, IndicatorItem
from app.schemas.ohlcv import OHLCVRecord
from app.services.custom_indicators import CUSTOM_INDICATORS, INDICATOR_ALIASES

settings = get_settings()

# Parameter synonyms mapper to bridge user-friendly names to TA-Lib official parameter names
PARAMETER_SYNONYMS: Dict[str, str] = {
    "period": "timeperiod",
    "length": "timeperiod",
    "n": "timeperiod",
    "window": "timeperiod",
    "fast_period": "fastperiod",
    "slow_period": "slowperiod",
    "signal_period": "signalperiod",
    "nb_dev_up": "nbdevup",
    "nb_dev_dn": "nbdevdn",
    "ma_type": "matype",
    "atr_length": "atr_period",
}


def sanitize_value(val: Any) -> Optional[float]:
    """Sanitize numpy/float values: convert NaN and Infinity to None (null in JSON)."""
    if val is None:
        return None
    try:
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return None
        return round(f_val, 4)
    except (TypeError, ValueError):
        return None


def normalize_talib_params(func_name: str, user_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize user-provided parameters to match TA-Lib's official parameter dictionary.
    E.g., maps {'period': 20} -> {'timeperiod': 20}.
    """
    try:
        f = ta.Function(func_name)
    except Exception as exc:
        raise InvalidIndicatorError(f"Failed to inspect indicator '{func_name}': {exc}") from exc

    official_params = f.parameters
    clean_official = {k.lower().replace("_", ""): k for k in official_params.keys()}
    normalized: Dict[str, Any] = {}

    for k, v in user_params.items():
        k_lower = str(k).lower().strip()
        if k_lower in PARAMETER_SYNONYMS and PARAMETER_SYNONYMS[k_lower] in official_params:
            target_key = PARAMETER_SYNONYMS[k_lower]
        elif k in official_params:
            target_key = k
        elif k_lower.replace("_", "") in clean_official:
            target_key = clean_official[k_lower.replace("_", "")]
        else:
            target_key = k

        if target_key in official_params:
            default_val = official_params[target_key]
            if isinstance(default_val, int) and not isinstance(default_val, bool):
                try:
                    v = int(v)
                except (ValueError, TypeError):
                    pass
            elif isinstance(default_val, float):
                try:
                    v = float(v)
                except (ValueError, TypeError):
                    pass

        normalized[target_key] = v

    return normalized


def generate_indicator_base_label(name: str, params: Dict[str, Any]) -> str:
    """Generate a clean, recognizable label for the indicator (e.g. SMA_20, MACD_12_26_9)."""
    if "timeperiod" in params and len(params) == 1:
        return f"{name}_{params['timeperiod']}"
    if "period" in params and len(params) == 1:
        return f"{name}_{params['period']}"
    if params:
        param_summary = "_".join(str(v) for v in params.values())
        return f"{name}_{param_summary}"
    return name


def resolve_effective_params(
    canonical_name: str,
    is_custom: bool,
    user_params: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns: (calc_params, display_params)
    - calc_params: normalized parameters passed to calculation engine
    - display_params: user-friendly parameters to return in API response
    """
    if is_custom:
        custom_def = CUSTOM_INDICATORS.get(canonical_name, {})
        default_params = dict(custom_def.get("parameters", {}))
        merged = dict(default_params)
        merged.update(user_params)
        return merged, merged

    try:
        f = ta.Function(canonical_name)
        official_defaults = dict(f.parameters)
    except Exception:
        official_defaults = {}

    calc_params = normalize_talib_params(canonical_name, user_params)

    # For display: start with official defaults, overlay normalized, and preserve user-friendly keys
    display_params = dict(official_defaults)
    display_params.update(calc_params)

    if user_params:
        for k, v in user_params.items():
            k_clean = str(k).strip()
            display_params[k_clean] = v
            # If user passed a friendly synonym like 'period', remove 'timeperiod' to avoid redundancy
            if (
                k_clean.lower() in ("period", "length", "n", "window")
                and "timeperiod" in display_params
                and "timeperiod" not in user_params
            ):
                del display_params["timeperiod"]

    return calc_params, display_params


def determine_indicator_labels(indicators: List[IndicatorItem]) -> List[str]:
    """
    Generate clean, collision-free output labels for requested indicators.
    - If indicator name is unique in request: use its clean requested name (e.g. 'SMA', 'MACD', 'DOJI').
    - If multiple indicators share the same name: disambiguate with params (e.g. 'SMA_20', 'SMA_50').
    """
    requested_names = [ind.name.strip().upper() for ind in indicators]
    counts: Dict[str, int] = {}
    for name in requested_names:
        counts[name] = counts.get(name, 0) + 1

    labels: List[str] = []
    used_labels = set()
    for ind in indicators:
        req_name = ind.name.strip().upper()
        if counts[req_name] == 1:
            chosen = req_name
        else:
            chosen = generate_indicator_base_label(req_name, ind.parameters)

        final_label = chosen
        idx = 2
        while final_label in used_labels:
            final_label = f"{chosen}_{idx}"
            idx += 1
        used_labels.add(final_label)
        labels.append(final_label)

    return labels


class IndicatorEngine:
    """High-performance technical indicator calculation engine powered by TA-Lib and NumPy."""

    def __init__(self, max_workers: Optional[int] = None):
        self._max_workers = max_workers or settings.MAX_WORKERS
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        self._available_talib_functions = set(talib.get_functions())
        self._custom_indicators = CUSTOM_INDICATORS
        self._aliases = INDICATOR_ALIASES

    def resolve_indicator(self, raw_name: str) -> Tuple[str, bool]:
        """
        Resolve indicator name through aliases and determine if it is custom or TA-Lib native.
        Returns: (canonical_name, is_custom)
        """
        clean_name = raw_name.strip().upper()

        # Check aliases first
        if clean_name in self._aliases:
            clean_name = self._aliases[clean_name]

        # Check custom indicator registry
        if clean_name in self._custom_indicators:
            return clean_name, True

        # Check TA-Lib native functions
        if clean_name in self._available_talib_functions:
            return clean_name, False

        # Not found
        supported_samples = sorted(list(self._custom_indicators.keys()) + ["SMA", "RSI", "MACD", "BBANDS", "ATR", "DOJI"])
        raise InvalidIndicatorError(
            f"Indicator '{raw_name}' is not supported.",
            details={
                "popular_samples": supported_samples,
                "total_supported": len(self._available_talib_functions) + len(self._custom_indicators),
                "list_url": "/api/v1/indicator/available",
            },
        )

    def _compute_single_indicator(
        self,
        label: str,
        canonical_name: str,
        is_custom: bool,
        user_params: Dict[str, Any],
        inputs: Dict[str, np.ndarray],
    ) -> Tuple[str, Dict[str, Any], List[Any]]:
        """
        Execute calculation for a single indicator (TA-Lib or Custom).
        Returns: (label, display_params, bar_values)
        where bar_values has length equal to the number of bars.
        Each bar value is:
        - float (sanitized) or None for single-output indicators
        - Dict[str, Optional[float]] for multi-output indicators
        """
        calc_params, display_params = resolve_effective_params(canonical_name, is_custom, user_params)
        n_bars = len(inputs["close"])

        if is_custom:
            custom_def = self._custom_indicators[canonical_name]
            calc_func = custom_def["func"]
            output_names = custom_def["output_names"]

            output_dict = calc_func(inputs, **calc_params)

            if len(output_names) == 1:
                # Single output (e.g. VWAP)
                arr = output_dict.get(output_names[0], np.full(n_bars, np.nan))
                bar_values = [sanitize_value(v) for v in arr]
            else:
                # Multi output (e.g. SUPERTREND, ICHIMOKU, KELTNER, PIVOT_POINTS, HEIKIN_ASHI)
                bar_values = []
                for i in range(n_bars):
                    bar_val = {
                        out_name: sanitize_value(output_dict.get(out_name, np.full(n_bars, np.nan))[i])
                        for out_name in output_names
                    }
                    bar_values.append(bar_val)

        else:
            # Native TA-Lib calculation
            f = ta.Function(canonical_name)
            f.parameters = calc_params
            output_names = f.output_names

            raw_output = f(inputs)

            if len(output_names) == 1 and not isinstance(raw_output, list):
                # Single output indicator (e.g. SMA, RSI, ATR, CDLDOJI)
                bar_values = [sanitize_value(v) for v in raw_output]
            else:
                # Multi output indicator (e.g. MACD, BBANDS, STOCH)
                output_arrays = raw_output if isinstance(raw_output, list) else [raw_output]
                bar_values = []
                for i in range(n_bars):
                    bar_val = {
                        out_name: sanitize_value(arr[i])
                        for out_name, arr in zip(output_names, output_arrays)
                    }
                    bar_values.append(bar_val)

        return label, display_params, bar_values

    async def calculate_indicators_for_records(
        self,
        records: List[OHLCVRecord],
        indicators: List[IndicatorItem],
    ) -> Tuple[List[CalculatedDataPoint], List[str]]:
        """
        Calculate indicators across records concurrently.
        Supports single and multiple tickers, ensuring chronological order and parallel execution.
        """
        if not records:
            return [], []

        if not indicators:
            data_points = [
                CalculatedDataPoint(
                    ticker=r.ticker,
                    trading_date=r.trade_date,
                    indicators={},
                    indicator={},
                )
                for r in records
            ]
            return data_points, []

        # Validate and resolve all indicators up front
        labels = determine_indicator_labels(indicators)
        validated_indicators = []
        for ind, label in zip(indicators, labels):
            canonical_name, is_custom = self.resolve_indicator(ind.name)
            validated_indicators.append((label, canonical_name, is_custom, ind.parameters))

        # Group records by ticker
        ticker_groups: Dict[str, List[OHLCVRecord]] = {}
        for r in records:
            ticker_groups.setdefault(r.ticker, []).append(r)

        calculated_points: List[CalculatedDataPoint] = []
        all_calculated_indicator_labels: List[str] = [item[0] for item in validated_indicators]

        loop = asyncio.get_running_loop()

        for ticker, t_records in ticker_groups.items():
            # 1. Sort records chronologically (trade_date ascending)
            sorted_records = sorted(t_records, key=lambda x: x.trade_date)
            n_bars = len(sorted_records)

            # 2. Build contiguous numpy float64 input arrays
            inputs: Dict[str, np.ndarray] = {
                "open": np.ascontiguousarray([r.open_price for r in sorted_records], dtype=np.float64),
                "high": np.ascontiguousarray([r.high_price for r in sorted_records], dtype=np.float64),
                "low": np.ascontiguousarray([r.low_price for r in sorted_records], dtype=np.float64),
                "close": np.ascontiguousarray([r.close_price for r in sorted_records], dtype=np.float64),
                "volume": np.ascontiguousarray([r.volume for r in sorted_records], dtype=np.float64),
            }

            # 3. Parallel calculation of indicators in thread pool
            tasks = [
                loop.run_in_executor(
                    self._executor,
                    self._compute_single_indicator,
                    label,
                    canonical_name,
                    is_custom,
                    params,
                    inputs,
                )
                for label, canonical_name, is_custom, params in validated_indicators
            ]

            computed_indicator_results = await asyncio.gather(*tasks)

            # 4. Collate indicator results per bar
            bar_indicators: List[Dict[str, Any]] = [{} for _ in range(n_bars)]

            for label, display_params, bar_values in computed_indicator_results:
                for i in range(n_bars):
                    bar_indicators[i][label] = {
                        "params": display_params,
                        "value": bar_values[i],
                    }

            # 5. Build enriched CalculatedDataPoint list
            for i, r in enumerate(sorted_records):
                calculated_points.append(
                    CalculatedDataPoint(
                        ticker=r.ticker,
                        trading_date=r.trade_date,
                        indicators=bar_indicators[i],
                        indicator=bar_indicators[i],
                    )
                )

        return calculated_points, all_calculated_indicator_labels

    def get_available_indicators(self) -> Dict[str, Any]:
        """Return comprehensive metadata of all supported indicators grouped by category."""
        talib_groups = talib.get_function_groups()
        result_groups: Dict[str, List[Dict[str, Any]]] = {}

        # 1. Add Custom Indicators
        custom_list = []
        for name, meta in self._custom_indicators.items():
            custom_list.append(
                {
                    "name": name,
                    "display_name": meta["display_name"],
                    "group": meta["group"],
                    "parameters": meta["parameters"],
                    "output_names": meta["output_names"],
                    "type": "custom",
                }
            )
        result_groups["Custom / Modern Indicators"] = custom_list

        # 2. Add TA-Lib grouped indicators
        for group_name, func_names in talib_groups.items():
            group_list = []
            for fname in sorted(func_names):
                try:
                    f = ta.Function(fname)
                    info = f.info
                    group_list.append(
                        {
                            "name": fname,
                            "display_name": info.get("display_name", fname),
                            "group": group_name,
                            "parameters": dict(info.get("parameters", {})),
                            "output_names": info.get("output_names", []),
                            "type": "talib",
                        }
                    )
                except Exception:
                    group_list.append(
                        {
                            "name": fname,
                            "display_name": fname,
                            "group": group_name,
                            "parameters": {},
                            "output_names": ["real"],
                            "type": "talib",
                        }
                    )
            result_groups[group_name] = group_list

        total_count = sum(len(items) for items in result_groups.values())
        return {
            "total_indicators": total_count,
            "aliases": self._aliases,
            "categories": result_groups,
        }

    def shutdown(self):
        """Shut down the thread pool executor cleanly."""
        self._executor.shutdown(wait=False)


# Singleton indicator engine instance
_indicator_engine_instance: Optional[IndicatorEngine] = None


def get_indicator_engine() -> IndicatorEngine:
    """Dependency injector for IndicatorEngine."""
    global _indicator_engine_instance
    if _indicator_engine_instance is None:
        _indicator_engine_instance = IndicatorEngine()
    return _indicator_engine_instance
