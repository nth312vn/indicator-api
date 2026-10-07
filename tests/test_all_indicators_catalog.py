import pytest
import talib
from app.schemas.indicator import IndicatorItem
from app.services.custom_indicators import CUSTOM_INDICATORS, INDICATOR_ALIASES
from app.services.indicator_engine import IndicatorEngine
from app.services.mock_fiin_service import generate_mock_ohlcv


@pytest.fixture(scope="module")
def sample_records():
    # 300 bars of historical OHLCV data
    response = generate_mock_ohlcv(tickers="AAPL", page_size=300)
    return response.data


@pytest.fixture(scope="module")
def engine():
    return IndicatorEngine(max_workers=8)


@pytest.mark.asyncio
async def test_all_custom_indicators_structure(engine, sample_records):
    """Test all custom indicators: verify structure is {params: ..., value: ...}."""
    for custom_name, meta in CUSTOM_INDICATORS.items():
        ind_item = IndicatorItem(name=custom_name)
        data_points, labels = await engine.calculate_indicators_for_records(
            records=sample_records,
            indicators=[ind_item],
        )

        assert len(data_points) == len(sample_records), f"Failed record length for {custom_name}"
        assert custom_name in labels

        last_bar = data_points[-1]
        assert custom_name in last_bar.indicators, f"Missing {custom_name} in indicators"
        ind_result = last_bar.indicators[custom_name]

        # Verify {params, value} keys
        assert "params" in ind_result, f"Missing 'params' in {custom_name}"
        assert "value" in ind_result, f"Missing 'value' in {custom_name}"
        assert isinstance(ind_result["params"], dict)

        val = ind_result["value"]
        if len(meta["output_names"]) == 1:
            assert isinstance(val, (float, int)), f"Expected float for single-output {custom_name}, got {type(val)}"
        else:
            assert isinstance(val, dict), f"Expected dict for multi-output {custom_name}, got {type(val)}"
            for out_name in meta["output_names"]:
                assert out_name in val, f"Missing output {out_name} in {custom_name}"


@pytest.mark.asyncio
async def test_all_talib_indicators_structure(engine, sample_records):
    """
    Test every TA-Lib native function supported by TA-Lib abstract interface.
    Ensures 100% calculation success and verified {params, value} structure.
    """
    all_functions = sorted(list(talib.get_functions()))
    # Functions that require special custom 2-series inputs like MAVP (variable period vector)
    skip_functions = {"MAVP"}

    test_functions = [f for f in all_functions if f not in skip_functions]

    success_count = 0
    failed_funcs = []

    # Test in batches to optimize execution
    batch_size = 20
    for i in range(0, len(test_functions), batch_size):
        batch = test_functions[i : i + batch_size]
        indicator_items = [IndicatorItem(name=fn) for fn in batch]

        try:
            data_points, labels = await engine.calculate_indicators_for_records(
                records=sample_records,
                indicators=indicator_items,
            )

            assert len(data_points) == len(sample_records)
            last_bar = data_points[-1]

            for fn in batch:
                assert fn in last_bar.indicators, f"Missing indicator {fn} in result"
                item = last_bar.indicators[fn]
                assert "params" in item, f"Missing 'params' in {fn}"
                assert "value" in item, f"Missing 'value' in {fn}"
                assert isinstance(item["params"], dict)

                val = item["value"]
                # Must be float/int or dict (or None if warmup/edge)
                assert val is None or isinstance(val, (float, int, dict)), f"Invalid value type for {fn}: {type(val)}"
                success_count += 1

        except Exception as exc:
            failed_funcs.append((batch, str(exc)))

    assert len(failed_funcs) == 0, f"Failed indicators: {failed_funcs}"
    print(f"\nSuccessfully verified {success_count} TA-Lib indicators with new {{params, value}} schema!")


@pytest.mark.asyncio
async def test_indicator_aliases_structure(engine, sample_records):
    """Test popular indicator aliases (DOJI, HAMMER, KC, PIVOT, etc.)."""
    aliases_to_test = ["DOJI", "HAMMER", "ENGULFING", "KC", "PIVOT", "HA"]
    items = [IndicatorItem(name=alias) for alias in aliases_to_test]

    data_points, labels = await engine.calculate_indicators_for_records(
        records=sample_records,
        indicators=items,
    )

    last_bar = data_points[-1]
    for alias in aliases_to_test:
        assert alias in last_bar.indicators
        assert "params" in last_bar.indicators[alias]
        assert "value" in last_bar.indicators[alias]
