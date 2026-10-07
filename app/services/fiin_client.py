from typing import Any, Dict, Optional
import httpx
from app.core.config import get_settings
from app.core.exceptions import FiinDataFetchError
from app.core.logging import logger
from app.schemas.ohlcv import FiinOHLCVResponse
from app.services.mock_fiin_service import generate_mock_ohlcv

settings = get_settings()


class FiinDataClient:
    """Async HTTP client to query OHLCV stock data from Fiin Data API."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client
        self._base_url = settings.FIIN_DATA_API_BASE_URL.rstrip("/")
        self._endpoint_path = settings.FIIN_DATA_API_PATH
        if not self._endpoint_path.startswith("/"):
            self._endpoint_path = "/" + self._endpoint_path

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None and not self._client.is_closed:
            return self._client
        # If client wasn't provided or closed, create dedicated client
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(settings.FIIN_API_TIMEOUT_SECONDS, connect=5.0),
            limits=httpx.Limits(
                max_keepalive_connections=settings.FIIN_MAX_KEEPALIVE_CONNECTIONS,
                max_connections=settings.FIIN_MAX_CONNECTIONS,
            ),
        )

    async def fetch_ohlcv(
        self,
        ticker: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> FiinOHLCVResponse:
        """
        Fetch OHLCV historical price data from Fiin stockist endpoint.

        Parameters:
            ticker: Stock ticker(s) - e.g. "AAPL" or "AAPL,MSFT"
            start_time: Start date/time
            end_time: End date/time
            page: Pagination page number
            page_size: Pagination page size
        """
        params: Dict[str, Any] = {
            "ticker": ticker,
            "page": page,
            "page_size": page_size,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        url = f"{self._base_url}{self._endpoint_path}"
        logger.info(f"Fetching OHLCV data from {url} with params: {params}")

        client = await self._get_client()
        owns_client = client != self._client

        try:
            response = await client.get(self._endpoint_path, params=params)
            response.raise_for_status()
            data_json = response.json()
            return FiinOHLCVResponse.model_validate(data_json)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning(f"Failed to query live Fiin API ({url}): {exc}")
            if settings.ENABLE_MOCK_FALLBACK:
                logger.info(f"Fallback to mock OHLCV generator for ticker(s)='{ticker}'")
                return generate_mock_ohlcv(
                    tickers=ticker,
                    start_time=start_time,
                    end_time=end_time,
                    page=page,
                    page_size=page_size,
                )
            raise FiinDataFetchError(
                message=f"Error fetching OHLCV data from upstream Fiin API: {str(exc)}",
                details={"url": url, "params": params},
            ) from exc
        finally:
            if owns_client:
                await client.aclose()


# Singleton client instance
_fiin_client_instance: Optional[FiinDataClient] = None


def get_fiin_client() -> FiinDataClient:
    """Dependency injector for FiinDataClient."""
    global _fiin_client_instance
    if _fiin_client_instance is None:
        _fiin_client_instance = FiinDataClient()
    return _fiin_client_instance
