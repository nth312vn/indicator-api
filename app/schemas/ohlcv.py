from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PaginationMetadata(BaseModel):
    """Pagination metadata model matching Fiin API response."""

    page: int = Field(1, description="Current page number")
    total_pages: int = Field(1, description="Total pages available")
    page_size: int = Field(100, description="Items per page")
    total_records: int = Field(0, description="Total number of records")

    model_config = ConfigDict(extra="ignore")


class OHLCVRecord(BaseModel):
    """Individual stock price bar record."""

    ticker: str = Field(..., description="Stock symbol/ticker")
    trade_date: str = Field(..., description="Trade date in YYYY-MM-DD or datetime format")
    open_price: float = Field(..., description="Open price")
    high_price: float = Field(..., description="High price")
    low_price: float = Field(..., description="Low price")
    close_price: float = Field(..., description="Close price")
    volume: float = Field(..., description="Trading volume")

    model_config = ConfigDict(extra="ignore")


class FiinOHLCVResponse(BaseModel):
    """Full response structure from Fiin data API."""

    status: str = Field("success", description="Status string: success or error")
    data: List[OHLCVRecord] = Field(default_factory=list, description="List of OHLCV bars")
    pagination: Optional[PaginationMetadata] = Field(None, description="Pagination metadata")

    model_config = ConfigDict(extra="ignore")
