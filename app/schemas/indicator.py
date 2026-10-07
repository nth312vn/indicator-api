from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class IndicatorItem(BaseModel):
    """Configuration for a single indicator calculation."""

    name: str = Field(..., description="Indicator name e.g. SMA, EMA, RSI, MACD, BBANDS, ATR, VWAP, SUPERTREND")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters e.g. {'period': 20}")

    model_config = ConfigDict(extra="ignore")


class IndicatorCalculateRequest(BaseModel):
    """
    Request body for calculating indicators.
    Accepts either a single indicator object or a list of indicators for parallel execution.
    """

    indicators: Union[IndicatorItem, List[IndicatorItem]] = Field(
        ...,
        description="Single indicator or list of indicators to calculate",
        examples=[
            {"name": "SMA", "parameters": {"period": 20}},
            [
                {"name": "SMA", "parameters": {"period": 20}},
                {"name": "RSI", "parameters": {"period": 14}},
                {"name": "MACD", "parameters": {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}},
            ],
        ],
    )

    @property
    def indicator_list(self) -> List[IndicatorItem]:
        """Normalize indicators into a list for uniform internal processing."""
        if isinstance(self.indicators, list):
            return self.indicators
        return [self.indicators]

    model_config = ConfigDict(extra="ignore")


class IndicatorValue(BaseModel):
    """Container for indicator parameters and calculated value."""

    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters used for calculation")
    value: Union[float, Dict[str, Optional[float]], None] = Field(
        None,
        description="Calculated value: float for single-line indicators, or dict of metrics for multi-line indicators",
    )

    model_config = ConfigDict(extra="ignore")


class CalculatedDataPoint(BaseModel):
    """OHLCV data point with calculated indicators formatted per specification."""

    ticker: str = Field(..., description="Mã cổ phiếu")
    trading_date: str = Field(..., description="Ngày giao dịch (YYYY-MM-DD)")
    indicators: Dict[str, Any] = Field(
        default_factory=dict,
        description="Các chỉ báo kỹ thuật theo cấu trúc {name: {'params': {...}, 'value': ...}}",
    )
    indicator: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Alias cho 'indicators' nhằm tương thích ngược",
    )

    model_config = ConfigDict(extra="ignore")


class IndicatorCalculateResponse(BaseModel):
    """
    Final API response for indicator calculations matching exact specification:
    {
        page,
        page_size,
        total_record,
        data: [
            {
                ticker,
                trading_date,
                indicators: {
                    "SMA": { "params": { "period": 20 }, "value": 149.52 },
                    "MACD": { "params": { ... }, "value": { "macd": ..., "macdsignal": ..., "macdhist": ... } }
                }
            }
        ]
    }
    """

    page: int = Field(1, description="Trang hiện tại")
    page_size: int = Field(100, description="Số lượng bản ghi trên một trang")
    total_record: int = Field(0, description="Tổng số bản ghi dữ liệu")
    data: List[CalculatedDataPoint] = Field(default_factory=list, description="Danh sách dữ liệu tính toán chỉ báo")

    model_config = ConfigDict(extra="ignore")

