import asyncio
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import get_settings
from app.core.exceptions import FiinDataFetchError
from app.core.logging import logger
from app.schemas.ohlcv import FiinOHLCVResponse, OHLCVRecord, PaginationMetadata
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
        fetch_all: bool = False,
        client: Optional[httpx.AsyncClient] = None,
    ) -> FiinOHLCVResponse:
        """
        Fetch OHLCV historical price data from Fiin stockist endpoint.

        Parameters:
            ticker: Stock ticker(s) - e.g. "AAPL" or "AAPL,MSFT"
            start_time: Start date/time
            end_time: End date/time
            page: Pagination page number
            page_size: Pagination page size
            fetch_all: If True, automatically paginates and fetches all available records
            client: Optional httpx.AsyncClient instance to reuse connections
        """
        if fetch_all:
            return await self.fetch_all_ohlcv(
                ticker=ticker,
                start_time=start_time,
                end_time=end_time,
                page_size=page_size,
                client=client,
            )

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

        target_client = client or await self._get_client()
        owns_client = (client is None) and (target_client != self._client)

        try:
            response = await target_client.get(self._endpoint_path, params=params)
            response.raise_for_status()
            data_json = response.json()
            return FiinOHLCVResponse.model_validate(data_json)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning(f"Failed to query live Fiin API ({url}): {exc}")
            if settings.ENABLE_MOCK_FALLBACK:
                logger.info(f"Fallback to mock OHLCV generator for ticker(s)='{ticker}' (page={page}, page_size={page_size})")
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
                await target_client.aclose()

    async def fetch_all_ohlcv(
        self,
        ticker: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page_size: Optional[int] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> FiinOHLCVResponse:
        """
        Fetch all OHLCV historical price data across all pages for the given ticker(s) and time range.
        Handles pagination automatically:
        1. Requests first page with specified page_size (defaults to settings.FIIN_FETCH_PAGE_SIZE).
        2. Detects total_pages from response metadata. If total_pages > 1, fetches remaining pages concurrently
           with bounded concurrency.
        3. If total_pages is not provided in metadata but the page is full, paginates sequentially until exhausted.
        4. Deduplicates and returns records chronologically sorted.
        """
        effective_page_size = page_size or settings.FIIN_FETCH_PAGE_SIZE
        target_client = client or await self._get_client()
        owns_client = (client is None) and (target_client != self._client)

        try:
            # 1. Fetch page 1
            first_response = await self.fetch_ohlcv(
                ticker=ticker,
                start_time=start_time,
                end_time=end_time,
                page=1,
                page_size=effective_page_size,
                client=target_client,
            )

            all_records: List[OHLCVRecord] = list(first_response.data)
            pagination = first_response.pagination

            # 2. Handle subsequent pages
            if pagination and pagination.total_pages > 1:
                total_pages = pagination.total_pages
                logger.info(
                    f"Fiin OHLCV pagination detected: total_pages={total_pages}, total_records={pagination.total_records}. "
                    f"Fetching pages 2..{total_pages} (page_size={effective_page_size}) for ticker='{ticker}'..."
                )
                semaphore = asyncio.Semaphore(min(settings.FIIN_MAX_KEEPALIVE_CONNECTIONS, 10))

                async def _fetch_single_page(p: int) -> List[OHLCVRecord]:
                    async with semaphore:
                        page_resp = await self.fetch_ohlcv(
                            ticker=ticker,
                            start_time=start_time,
                            end_time=end_time,
                            page=p,
                            page_size=effective_page_size,
                            client=target_client,
                        )
                        return page_resp.data

                tasks = [_fetch_single_page(p) for p in range(2, total_pages + 1)]
                results = await asyncio.gather(*tasks)
                for page_data in results:
                    all_records.extend(page_data)

            elif len(first_response.data) == effective_page_size:
                # If pagination metadata is missing or total_pages not given, but page 1 was full
                logger.info(
                    f"Page 1 returned full page_size={effective_page_size} without total_pages metadata. "
                    f"Paginating sequentially..."
                )
                curr_page = 2
                max_safety_pages = 200
                while curr_page <= max_safety_pages:
                    next_resp = await self.fetch_ohlcv(
                        ticker=ticker,
                        start_time=start_time,
                        end_time=end_time,
                        page=curr_page,
                        page_size=effective_page_size,
                        client=target_client,
                    )
                    if not next_resp.data:
                        break
                    all_records.extend(next_resp.data)
                    if len(next_resp.data) < effective_page_size:
                        break
                    curr_page += 1

            # 3. Deduplicate records by (ticker, trade_date) and sort chronologically
            unique_records: Dict[tuple, OHLCVRecord] = {}
            for r in all_records:
                unique_records[(r.ticker, r.trade_date)] = r

            sorted_records = sorted(unique_records.values(), key=lambda r: (r.trade_date, r.ticker))
            total_records = len(sorted_records)

            logger.info(
                f"Fetched total {total_records} OHLCV records for ticker(s)='{ticker}' "
                f"(range: {start_time or 'start'} to {end_time or 'latest'})."
            )

            return FiinOHLCVResponse(
                status="success",
                data=sorted_records,
                pagination=PaginationMetadata(
                    page=1,
                    total_pages=1,
                    page_size=total_records,
                    total_records=total_records,
                ),
            )
        finally:
            if owns_client:
                await target_client.aclose()


# Singleton client instance
_fiin_client_instance: Optional[FiinDataClient] = None


def get_fiin_client() -> FiinDataClient:
    """Dependency injector for FiinDataClient."""
    global _fiin_client_instance
    if _fiin_client_instance is None:
        _fiin_client_instance = FiinDataClient()
    return _fiin_client_instance
