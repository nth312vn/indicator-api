import pytest
import httpx
from httpx import ASGITransport
from app.main import app
from app.services.fiin_client import FiinDataClient
from app.schemas.ohlcv import FiinOHLCVResponse, OHLCVRecord, PaginationMetadata


@pytest.mark.asyncio
async def test_fiin_client_fetch_ohlcv_single_page():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        client = FiinDataClient(client=http_client)
        resp = await client.fetch_ohlcv(ticker="AAPL", page=1, page_size=15)

        assert isinstance(resp, FiinOHLCVResponse)
        assert resp.status == "success"
        assert len(resp.data) == 15
        assert resp.pagination is not None
        assert resp.pagination.page == 1
        assert resp.pagination.page_size == 15


@pytest.mark.asyncio
async def test_fiin_client_fetch_all_ohlcv_pagination_gather():
    """Test fetch_all_ohlcv accurately paginates and combines all pages when total_pages > 1."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        client = FiinDataClient(client=http_client)
        # Using a small page_size of 20 to trigger multi-page fetching from mock service (~108 bars total)
        resp = await client.fetch_all_ohlcv(ticker="AAPL", page_size=20)

        assert isinstance(resp, FiinOHLCVResponse)
        assert resp.status == "success"
        # Total bars should be > 20 since it fetched all pages
        assert len(resp.data) > 50
        assert resp.pagination is not None
        assert resp.pagination.total_records == len(resp.data)

        # Ensure bars are sorted chronologically
        dates = [r.trade_date for r in resp.data]
        assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_fiin_client_fetch_ohlcv_with_fetch_all_flag():
    """Test fetch_ohlcv with fetch_all=True delegates to fetch_all_ohlcv."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        client = FiinDataClient(client=http_client)
        resp = await client.fetch_ohlcv(ticker="AAPL", page_size=25, fetch_all=True)

        assert isinstance(resp, FiinOHLCVResponse)
        assert len(resp.data) > 50
        assert resp.pagination.total_records == len(resp.data)


@pytest.mark.asyncio
async def test_fiin_client_sequential_pagination_when_total_pages_missing():
    """Test sequential pagination fallback when pagination metadata does not specify total_pages."""
    # Create custom transport that returns page 1 and page 2 without total_pages metadata
    def mock_handler(request: httpx.Request):
        url = request.url
        page = int(url.params.get("page", 1))
        page_size = int(url.params.get("page_size", 5))

        if page == 1:
            records = [
                {"ticker": "TEST", "trade_date": f"2024-01-0{i}", "open_price": 10.0, "high_price": 11.0, "low_price": 9.0, "close_price": 10.5, "volume": 1000.0}
                for i in range(1, 6)
            ]
            return httpx.Response(200, json={"status": "success", "data": records, "pagination": None})
        elif page == 2:
            records = [
                {"ticker": "TEST", "trade_date": f"2024-01-0{i}", "open_price": 10.0, "high_price": 11.0, "low_price": 9.0, "close_price": 10.5, "volume": 1000.0}
                for i in range(6, 8)
            ]
            return httpx.Response(200, json={"status": "success", "data": records, "pagination": None})
        else:
            return httpx.Response(200, json={"status": "success", "data": [], "pagination": None})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://upstream") as http_client:
        client = FiinDataClient(client=http_client)
        resp = await client.fetch_all_ohlcv(ticker="TEST", page_size=5)

        assert len(resp.data) == 7
        assert resp.data[0].trade_date == "2024-01-01"
        assert resp.data[-1].trade_date == "2024-01-07"
