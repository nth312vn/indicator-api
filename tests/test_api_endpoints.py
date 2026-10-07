import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_fiin_stockist_endpoint(client):
    response = await client.get(
        "/api/v1/portfolio-construction/fiin_data/stockist",
        params={"ticker": "AAPL", "page": 1, "page_size": 10},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "data" in json_data
    assert len(json_data["data"]) == 10
    record = json_data["data"][0]
    assert record["ticker"] == "AAPL"
    assert "open_price" in record
    assert "close_price" in record


@pytest.mark.asyncio
async def test_list_available_indicators(client):
    response = await client.get("/api/v1/indicator/available")
    assert response.status_code == 200
    json_data = response.json()
    assert "total_indicators" in json_data
    assert json_data["total_indicators"] >= 200
    assert "categories" in json_data


@pytest.mark.asyncio
async def test_calculate_single_indicator_new_response_schema(client):
    """Test response schema: {page, page_size, total_record, data: [{ticker, trading_date, indicators: {SMA: {params, value}}}]}"""
    payload = {
        "indicators": {
            "name": "SMA",
            "parameters": {
                "period": 20,
            },
        }
    }
    response = await client.post(
        "/api/v1/indicator/calculate",
        params={"ticker": "AAPL", "page": 1, "page_size": 30},
        json=payload,
    )
    assert response.status_code == 200
    json_data = response.json()

    # Root fields validation
    assert "page" in json_data
    assert "page_size" in json_data
    assert "total_record" in json_data
    assert "data" in json_data
    assert json_data["page"] == 1
    assert json_data["page_size"] == 30
    assert json_data["total_record"] > 0

    bars = json_data["data"]
    assert len(bars) == 30
    first_bar = bars[0]
    # Check item schema: ticker, trading_date, indicators
    assert "ticker" in first_bar
    assert first_bar["ticker"] == "AAPL"
    assert "trading_date" in first_bar
    assert "indicators" in first_bar
    assert "indicator" in first_bar
    assert "SMA" in first_bar["indicators"]
    assert first_bar["indicators"]["SMA"]["value"] is not None
    assert isinstance(first_bar["indicators"]["SMA"]["value"], float)
    assert first_bar["indicators"]["SMA"]["params"] == {"period": 20}

    # All bars should have valid float SMA
    last_bar = bars[-1]
    assert last_bar["indicators"]["SMA"]["value"] is not None
    assert isinstance(last_bar["indicators"]["SMA"]["value"], float)


@pytest.mark.asyncio
async def test_calculate_multiple_tickers_comma_and_repeat(client):
    """Test multi-ticker support: both comma-separated and repeated params."""
    payload = {
        "indicators": {
            "name": "SMA",
            "parameters": {"period": 10},
        }
    }

    # Case 1: Comma-separated ?ticker=AAPL,MSFT
    response_comma = await client.post(
        "/api/v1/indicator/calculate?ticker=AAPL,MSFT&page=1&page_size=200",
        json=payload,
    )
    assert response_comma.status_code == 200
    data_comma = response_comma.json()
    tickers_comma = {item["ticker"] for item in data_comma["data"]}
    assert "AAPL" in tickers_comma
    assert "MSFT" in tickers_comma

    # Case 2: Repeated params ?ticker=AAPL&ticker=MSFT
    response_repeat = await client.post(
        "/api/v1/indicator/calculate?ticker=AAPL&ticker=MSFT&page=1&page_size=200",
        json=payload,
    )
    assert response_repeat.status_code == 200
    data_repeat = response_repeat.json()
    tickers_repeat = {item["ticker"] for item in data_repeat["data"]}
    assert "AAPL" in tickers_repeat
    assert "MSFT" in tickers_repeat


@pytest.mark.asyncio
async def test_calculate_multiple_indicators_list_body(client):
    """Test multiple indicators passed as a list for parallel execution."""
    payload = {
        "indicators": [
            {"name": "SMA", "parameters": {"period": 20}},
            {"name": "RSI", "parameters": {"period": 14}},
            {"name": "VWAP"},
            {"name": "SUPERTREND", "parameters": {"period": 10, "multiplier": 3.0}},
            {"name": "DOJI"},
        ]
    }
    response = await client.post(
        "/api/v1/indicator/calculate",
        params={"ticker": "AAPL", "page": 1, "page_size": 50},
        json=payload,
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["page"] == 1
    assert json_data["page_size"] == 50
    assert json_data["total_record"] > 0

    last_bar = json_data["data"][-1]
    assert "ticker" in last_bar
    assert "trading_date" in last_bar
    assert "indicators" in last_bar
    assert "indicator" in last_bar

    # Check each indicator's structured response
    assert last_bar["indicators"]["SMA"]["value"] is not None
    assert isinstance(last_bar["indicators"]["SMA"]["value"], float)
    assert last_bar["indicators"]["SMA"]["params"] == {"period": 20}

    assert last_bar["indicators"]["RSI"]["value"] is not None
    assert isinstance(last_bar["indicators"]["RSI"]["value"], float)

    assert last_bar["indicators"]["VWAP"]["value"] is not None
    assert isinstance(last_bar["indicators"]["VWAP"]["value"], float)

    assert last_bar["indicators"]["SUPERTREND"]["value"]["supertrend"] is not None
    assert last_bar["indicators"]["SUPERTREND"]["params"] == {"period": 10, "multiplier": 3.0}

    assert last_bar["indicators"]["DOJI"]["value"] is not None


@pytest.mark.asyncio
async def test_calculate_macd_and_sma_exact_format(client):
    """Test exact user requested format: indicators: {'SMA': {params, value}, 'MACD': {params, value}}"""
    payload = {
        "indicators": [
            {"name": "SMA", "parameters": {"period": 20}},
            {"name": "MACD", "parameters": {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}},
        ]
    }
    response = await client.post(
        "/api/v1/indicator/calculate",
        params={"ticker": "AAPL", "page": 1, "page_size": 5},
        json=payload,
    )
    assert response.status_code == 200
    json_data = response.json()
    first_bar = json_data["data"][0]

    # Verify SMA
    assert "SMA" in first_bar["indicators"]
    assert first_bar["indicators"]["SMA"]["params"] == {"period": 20}
    assert isinstance(first_bar["indicators"]["SMA"]["value"], float)

    # Verify MACD
    assert "MACD" in first_bar["indicators"]
    assert first_bar["indicators"]["MACD"]["params"] == {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}
    macd_val = first_bar["indicators"]["MACD"]["value"]
    assert isinstance(macd_val, dict)
    assert "macd" in macd_val
    assert "macdsignal" in macd_val
    assert "macdhist" in macd_val


@pytest.mark.asyncio
async def test_calculate_macd_nested_and_flat(client):
    """Test MACD multi-output representations: nested vs flat."""
    payload = {
        "indicators": {
            "name": "MACD",
            "parameters": {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9},
        }
    }

    # 1. Test flatten_output=false (Nested Only - standard)
    resp_nested = await client.post(
        "/api/v1/indicator/calculate?ticker=AAPL&flatten_output=false&page=1&page_size=5",
        json=payload,
    )
    assert resp_nested.status_code == 200
    bar_nested = resp_nested.json()["data"][0]
    assert "MACD" in bar_nested["indicators"]
    assert isinstance(bar_nested["indicators"]["MACD"]["value"], dict)
    assert "macd" in bar_nested["indicators"]["MACD"]["value"]
    assert "macdsignal" in bar_nested["indicators"]["MACD"]["value"]
    assert "macdhist" in bar_nested["indicators"]["MACD"]["value"]

    # 2. Test flatten_output=true (Flat Only)
    resp_flat = await client.post(
        "/api/v1/indicator/calculate?ticker=AAPL&flatten_output=true&page=1&page_size=5",
        json=payload,
    )
    assert resp_flat.status_code == 200
    bar_flat = resp_flat.json()["data"][0]
    assert "MACD_macd" in bar_flat["indicators"]
    assert "MACD_macdsignal" in bar_flat["indicators"]
    assert "MACD_macdhist" in bar_flat["indicators"]
    assert "value" in bar_flat["indicators"]["MACD_macd"]


@pytest.mark.asyncio
async def test_calculate_invalid_indicator(client):
    payload = {
        "indicators": {
            "name": "UNKNOWN_INDICATOR_XYZ",
            "parameters": {},
        }
    }
    response = await client.post(
        "/api/v1/indicator/calculate",
        params={"ticker": "AAPL"},
        json=payload,
    )
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["status"] == "error"
    assert "not supported" in json_data["message"]


@pytest.mark.asyncio
async def test_calculate_missing_ticker_query_param(client):
    payload = {
        "indicators": {
            "name": "SMA",
            "parameters": {"period": 20},
        }
    }
    response = await client.post(
        "/api/v1/indicator/calculate",
        json=payload,
    )
    assert response.status_code == 422
