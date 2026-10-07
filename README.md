# Technical Indicator Calculation API (FastAPI & TA-Lib)

Hệ thống API tính toán các chỉ báo kỹ thuật chứng khoán (Technical Indicators) hiệu năng cao được xây dựng bằng **FastAPI**, **TA-Lib (C-Extension)**, **NumPy**, và **HTTPX**.

Hỗ trợ **hơn 207+ chỉ báo kỹ thuật** từ TA-Lib kết hợp với các **Custom Indicators hiện đại** (VWAP, SuperTrend, Ichimoku Cloud, Keltner Channel, Heikin-Ashi, Pivot Points) và các tên gọi tắt thân thiện (Aliases cho mô hình nến Nhật).

- 📖 **Tài liệu chi tiết 207+ Indicators**: [docs/INDICATORS.md](docs/INDICATORS.md)
- 📊 **Báo cáo kiểm thử hiệu năng 1 năm dữ liệu**: [docs/PERFORMANCE_BENCHMARK.md](docs/PERFORMANCE_BENCHMARK.md)

---

## 🚀 Các tính năng chính

1. **Kho chỉ báo đồ sộ (207+ Indicators)**:
   - **Custom & Modern Indicators**:
     - `VWAP`: Volume Weighted Average Price
     - `SUPERTREND` (hoặc `SUPER_TREND`): Chỉ báo theo xu hướng kèm ATR trailing bands và trend direction
     - `ICHIMOKU`: Mây Ichimoku (Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B)
     - `KELTNER` (hoặc `KC`): Keltner Channel (Upper, Middle, Lower)
     - `PIVOT_POINTS` (hoặc `PIVOT`): Classic Pivot Points (P, R1, R2, R3, S1, S2, S3)
     - `HEIKIN_ASHI` (hoặc `HA`): Làm mượt nến Heikin-Ashi (Open, High, Low, Close)
   - **Toàn bộ 201 chỉ báo native TA-Lib**:
     - **Overlap Studies** (25): SMA, EMA, WMA, DEMA, TEMA, KAMA, BBANDS, SAR, DONCHIAN, ACCBANDS,...
     - **Momentum Indicators** (47): RSI, MACD, STOCH, STOCHRSI, MOM, ROC, CCI, ADX, WILLR, MFI,...
     - **Volume Indicators** (12): OBV, AD, ADOSC, CMF (Chaikin Money Flow), EFI (Elder Force),...
     - **Volatility Indicators** (7): ATR, NATR, TRANGE, ADR, CVI,...
     - **Pattern Recognition (Mô hình nến Nhật)** (61): CDLDOJI, CDLHAMMER, CDLENGULFING, CDLMORNINGSTAR, CDLEVENINGSTAR,...
       *(Hỗ trợ viết tắt thân thiện: `DOJI`, `HAMMER`, `ENGULFING`, `MORNING_STAR`, `SHOOTING_STAR`,...)*
     - **Price Transform** & **Statistics**: MEDPRICE, TYPPRICE, BETA, CORREL, LINEARREG, STDDEV,...

2. **Endpoint tra cứu danh mục (`GET /api/v1/indicator/available`)**:
   - Trả về toàn bộ danh mục 207+ chỉ báo được phân loại theo nhóm, kèm theo mô tả, danh sách tham số (parameters), output names và các aliases.

3. **Tích hợp Fiin Data OHLCV API**:
   - Gọi bất đồng bộ (async HTTP) với connection pooling đến endpoint:
     `GET /api/v1/portfolio-construction/fiin_data/stockist`
   - Nhận các tham số: `ticker`, `start_time`, `end_time`, `page`, `page_size`.
   - Cơ chế tự động fallback sang mock data generator chân thực phục vụ kiểm thử và phát triển cục bộ độc lập.

4. **Endpoint tính toán chỉ báo (`POST /api/v1/indicator/calculate`)**:
   - Query Parameters: `ticker`, `start_date`, `end_date`, `page`, `page_size`.
   - Hỗ trợ linh hoạt 2 định dạng Request Body:
     - **Chỉ báo đơn lẻ**:
       ```json
       {
         "indicators": {
           "name": "SMA",
           "parameters": { "period": 20 }
         }
       }
       ```
     - **Danh sách nhiều chỉ báo (xử lý song song)**:
       ```json
       {
         "indicators": [
           { "name": "SMA", "parameters": { "period": 20 } },
           { "name": "RSI", "parameters": { "period": 14 } },
           { "name": "MACD", "parameters": { "fastperiod": 12, "slowperiod": 26, "signalperiod": 9 } },
           { "name": "BBANDS", "parameters": { "period": 20 } },
           { "name": "VWAP" },
           { "name": "SUPERTREND", "parameters": { "period": 10, "multiplier": 3.0 } },
           { "name": "DOJI" }
         ]
       }
       ```

5. **Tối ưu hóa hiệu năng & Xử lý song song (Concurrency)**:
   - Sử dụng `ThreadPoolExecutor` kết hợp `asyncio.gather()` để tính toán đồng thời nhiều chỉ báo.
   - TA-Lib là thư viện native C giải phóng GIL, tận dụng tối đa năng lực CPU đa nhân mà không tốn chi phí IPC process serialization.
   - Thử nghiệm thực tế: tính toán **12 chỉ báo kỹ thuật đồng thời chỉ mất ~7.5 ms**.

6. **Chuẩn hóa tham số & JSON Safe RFC 8259**:
   - Tự động map `period` / `length` $\rightarrow$ `timeperiod`.
   - Chuyển toàn bộ giá trị `NaN` và `Infinity` trong chu kỳ warm-up thành `null` (`None`).
   - Tự động sắp xếp dữ liệu theo `trade_date ASC`.

---

## 📁 Cấu trúc dự án

```
indicator_api/
├── .venv/                         # Virtual environment
├── app/
│   ├── main.py                    # Entry point FastAPI, Lifespan & Middleware
│   ├── core/
│   │   ├── config.py              # Pydantic Settings
│   │   ├── logging.py             # Loguru logger
│   │   └── exceptions.py          # Custom Exception handlers
│   ├── schemas/
│   │   ├── ohlcv.py               # Schemas cho Fiin OHLCV API
│   │   └── indicator.py           # Schemas Request/Response Indicator
│   ├── services/
│   │   ├── fiin_client.py         # Async HTTP client gọi Fiin API (connection pool)
│   │   ├── custom_indicators.py   # Engine tính VWAP, SuperTrend, Ichimoku, Keltner, Heikin-Ashi, Pivot
│   │   ├── indicator_engine.py    # TA-Lib engine tính toán song song đa chỉ báo
│   │   └── mock_fiin_service.py   # Realistic Mock OHLCV generator
│   └── api/
│       └── v1/
│           ├── router.py          # API v1 Router
│           └── endpoints/
│               ├── indicator.py   # POST /api/v1/indicator/calculate & GET /available
│               └── fiin_mock.py   # GET /api/v1/portfolio-construction/fiin_data/stockist
├── tests/
│   ├── test_indicator_engine.py   # Unit tests tính toán TA-Lib & Custom indicators
│   ├── test_api_endpoints.py      # Integration tests FastAPI endpoints
│   └── test_parallel_perf.py      # Benchmark test hiệu năng song song
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🛠️ Hướng dẫn cài đặt & Khởi chạy

### 1. Kích hoạt Virtual Environment

Trên Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Khởi chạy Server

```powershell
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger UI (Interactive Docs)**: http://localhost:8000/docs
- **Danh sách 207+ Indicators hỗ trợ**: http://localhost:8000/api/v1/indicator/available
- **Health Check**: http://localhost:8000/health

---

## 📡 Ví dụ gọi API (cURL)

### 1. Lấy danh mục tất cả các chỉ báo hỗ trợ:
```bash
curl -X GET "http://localhost:8000/api/v1/indicator/available"
```

### 2. Tính 1 chỉ báo (Ví dụ SMA 20):
```bash
curl -X POST "http://localhost:8000/api/v1/indicator/calculate?ticker=AAPL&page=1&page_size=30" \
     -H "Content-Type: application/json" \
     -d '{
       "indicators": {
         "name": "SMA",
         "parameters": {
           "period": 20
         }
       }
     }'
```

### 3. Tính đồng thời nhiều chỉ báo (SMA, RSI, MACD, BBANDS, VWAP, SuperTrend, Doji):
```bash
curl -X POST "http://localhost:8000/api/v1/indicator/calculate?ticker=AAPL&page=1&page_size=50" \
     -H "Content-Type: application/json" \
     -d '{
       "indicators": [
         { "name": "SMA", "parameters": { "period": 20 } },
         { "name": "RSI", "parameters": { "period": 14 } },
         { "name": "MACD", "parameters": { "fastperiod": 12, "slowperiod": 26, "signalperiod": 9 } },
         { "name": "BBANDS", "parameters": { "period": 20 } },
         { "name": "VWAP" },
         { "name": "SUPERTREND", "parameters": { "period": 10, "multiplier": 3.0 } },
         { "name": "DOJI" }
       ]
     }'
```

### 4. Tính toán cho nhiều mã cổ phiếu (Multi-Ticker):
Hỗ trợ cả 2 cách truyền tham số:
- Ngăn cách bằng dấu phẩy: `?ticker=AAPL,MSFT`
- Hoặc lặp lại query param: `?ticker=AAPL&ticker=MSFT`

```bash
curl -X POST "http://localhost:8000/api/v1/indicator/calculate?ticker=AAPL,MSFT&page=1&page_size=20" \
     -H "Content-Type: application/json" \
     -d '{
       "indicators": {
         "name": "SMA",
         "parameters": { "period": 20 }
       }
     }'
```

### 5. Cấu trúc Response chuẩn:
```json
{
  "page": 1,
  "page_size": 20,
  "total_record": 216,
  "data": [
    {
      "ticker": "AAPL",
      "trading_date": "2024-06-01",
      "indicators": {
        "SMA": {
          "params": {
            "period": 20
          },
          "value": 172.50
        },
        "MACD": {
          "params": {
            "fastperiod": 12,
            "slowperiod": 26,
            "signalperiod": 9
          },
          "value": {
            "macd": 0.8395,
            "macdsignal": 0.2836,
            "macdhist": 0.5559
          }
        }
      }
    }
  ]
}
```
*(Hỗ trợ cả trường `indicator` làm alias tương thích ngược với các client cũ).*

---

## 🧪 Chạy Test Suite

Chạy toàn bộ 23 bài test tự động (bao gồm unit tests, test tất cả 200+ chỉ báo TA-Lib & Custom, multi-ticker, schema test, và parallel benchmark):
```powershell
.\.venv\Scripts\pytest -v
```

