# Báo cáo kiểm thử hiệu năng (Performance Benchmark Report)

- **Thời gian đo kiểm**: 2026-10-07
- **Dataset**: Dữ liệu OHLCV 1 năm giao dịch thực tế (2025-01-01 đến 2025-12-31, tổng cộng **261 phiên giao dịch / nến**)
- **Mã cổ phiếu**: `AAPL`
- **Môi trường đo kiểm**:
  - Python 3.13.2 (Windows AMD64)
  - Framework: FastAPI + Uvicorn + Starlette
  - Thư viện tính toán: `TA-Lib 0.8.1` (C-extension Native) + `NumPy 2.5.3`
  - Concurrency: `ThreadPoolExecutor` kết hợp `asyncio.gather()`
- **Phương pháp**: Đo kiểm End-to-End (E2E) round-trip thực tế qua HTTP client:
  1. Nhận HTTP request & parse JSON request body
  2. Validate Pydantic schema
  3. Fetch 261 bars dữ liệu lịch sử 1 năm từ Fiin OHLCV Service
  4. Sắp xếp dữ liệu theo ngày tăng dần (`trade_date ASC`)
  5. Chuyển đổi sang mảng contiguous `numpy.float64`
  6. Phân luồng tính toán song song đa chỉ báo qua `ThreadPoolExecutor`
  7. Làm sạch giá trị `NaN` thành `null` chuẩn JSON RFC 8259
  8. Gói dữ liệu và serialize JSON phản hồi về cho client

---

## 📊 Bảng kết quả kiểm thử với số lượng Indicators tăng dần

| Số lượng Indicators | Số nến (1 Năm) | Engine Compute (ms) | E2E Latency Avg (ms) | P50 Median (ms) | P95 (ms) | Min / Max Latency (ms) | Throughput (RPS) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1 Indicator** | 261 bars | **12.31 ms** | **17.20 ms** | 16.10 ms | 24.23 ms | 13.53 / 24.23 ms | **58.1 req/s** |
| **5 Indicators** | 261 bars | **15.72 ms** | **20.56 ms** | 20.28 ms | 26.25 ms | 18.45 / 26.25 ms | **48.6 req/s** |
| **10 Indicators** | 261 bars | **21.67 ms** | **27.76 ms** | 27.11 ms | 33.43 ms | 26.34 / 33.43 ms | **36.0 req/s** |
| **20 Indicators** | 261 bars | **48.24 ms** | **57.68 ms** | 50.67 ms | 113.09 ms | 45.22 / 113.09 ms | **17.3 req/s** |
| **30 Indicators** | 261 bars | **45.75 ms** | **56.12 ms** | 56.97 ms | 59.77 ms | 51.25 / 59.77 ms | **17.8 req/s** |
| **50 Indicators** | 261 bars | **59.15 ms** | **71.49 ms** | 72.15 ms | 77.91 ms | 64.78 / 77.91 ms | **14.0 req/s** |

---

## 🔍 Phân tích chi tiết & Đánh giá hiệu năng

### 1. Hiệu năng tính toán của Engine TA-Lib C & NumPy
- **Khối lượng công việc**: Với 50 indicators trên 261 nến, hệ thống phải tính toán và trả về hơn **13,050 điểm dữ liệu chỉ báo**.
- **Thời gian xử lý của Engine**: Chỉ mất **59.15 ms** cho toàn bộ 50 chỉ báo (trung bình chỉ khoảng **~1.18 ms trên mỗi chỉ báo**).
- **Lợi thế C-Extension**: Thư viện TA-Lib được viết bằng mã C thuần, khi thực thi tính toán trên mảng NumPy `float64` liên tục (contiguous memory), tốc độ đạt mức vi giây (microseconds).

### 2. Tác động của cơ chế xử lý song song (ThreadPoolExecutor + GIL Release)
- Trong Python, các hàm tính toán của TA-Lib giải phóng khóa GIL (Global Interpreter Lock) trong quá trình tính toán trên mảng C.
- Việc sử dụng `ThreadPoolExecutor` cho phép các luồng tính toán chạy đồng thời trên các nhân CPU vật lý mà không bị nghẽn bởi GIL.
- **Không tốn chi phí IPC**: So với `ProcessPoolExecutor`, ThreadPool chia sẻ trực tiếp con trỏ bộ nhớ (pointer zero-copy) của các mảng NumPy `open, high, low, close, volume` giữa các luồng mà không phải tốn thời gian pickle/serialize qua lại giữa các tiến trình.

### 3. Latency End-to-End & JSON Serialization
- Với 1 - 10 indicators, toàn bộ thời gian xử lý E2E duy trì ở mức **17 ms - 27 ms**.
- Với 50 indicators, tổng thời gian phản hồi E2E chỉ là **71.49 ms**, hoàn toàn đáp ứng tiêu chuẩn khắt khe của các hệ thống trading realtime và backtesting (thường yêu cầu dưới 100 ms).

### 4. Cách tái tạo bài kiểm thử (Reproduce Benchmark)
Để tự chạy lại bài test benchmark này trên máy tính của bạn:
```powershell
.\.venv\Scripts\python.exe scripts/benchmark_performance.py
```