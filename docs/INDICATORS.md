# Tài liệu chi tiết các Indicators hỗ trợ (Technical Indicators Reference)

Hệ thống hỗ trợ hơn **207+ Technical Indicators**, bao gồm các **Custom Indicators hiện đại** và toàn bộ **201 hàm native từ TA-Lib**.

---

## MỤC LỤC
1. [Cách biểu diễn các chỉ báo đa đầu ra (MACD, BBANDS, STOCH)](#-cách-biểu-diễn-các-chỉ-báo-đa-đầu-ra-multi-output-indicators)
2. [Custom / Modern Indicators](#1-custom--modern-indicators)
3. [TA-Lib: Overlap Studies (Đường xu hướng & Dải giá)](#2-ta-lib-overlap-studies)
4. [TA-Lib: Momentum Indicators (Chỉ báo động lượng)](#3-ta-lib-momentum-indicators)
5. [TA-Lib: Volume Indicators (Chỉ báo khối lượng)](#4-ta-lib-volume-indicators)
6. [TA-Lib: Volatility Indicators (Chỉ báo biến động)](#5-ta-lib-volatility-indicators)
7. [TA-Lib: Pattern Recognition (Mô hình nến Nhật & Aliases)](#6-ta-lib-pattern-recognition)
8. [TA-Lib: Price Transform (Biến đổi giá)](#7-ta-lib-price-transform)
9. [TA-Lib: Statistic Functions (Hàm thống kê)](#8-ta-lib-statistic-functions)
10. [TA-Lib: Cycle Indicators (Chỉ báo chu kỳ sóng)](#9-ta-lib-cycle-indicators)

---

## 📌 Cách biểu diễn các chỉ báo đa đầu ra (Multi-Output Indicators)

Các chỉ báo như **MACD**, **Bollinger Bands (BBANDS)**, **Stochastic (STOCH)**, **Ichimoku**, **SuperTrend** trả về nhiều đường giá trị cùng lúc trong mỗi nến.

Hệ thống hỗ trợ 2 định dạng biểu diễn qua Query Param `flatten_output`:

### 1. Dạng Nested Object (Khuyên dùng - `flatten_output=false`):
Mỗi chỉ báo là một Object gom nhóm các đường giá trị thành phần, cực kỳ gọn gàng và dễ bóc tách trong code:
```json
"indicator": {
  "SMA_20": 172.50,
  "MACD_12_26_9": {
    "macd": 1.4523,
    "macdsignal": 1.1850,
    "macdhist": 0.2673
  },
  "BBANDS_20": {
    "upperband": 178.40,
    "middleband": 172.50,
    "lowerband": 166.60
  }
}
```

### 2. Dạng Flat Keys (`flatten_output=true`):
Các đường giá trị được làm phẳng thành các key đơn lẻ, phù hợp khi nạp trực tiếp vào thư viện biểu đồ (TradingView Charts, Highcharts) hoặc xuất file CSV/Excel:
```json
"indicator": {
  "SMA_20": 172.50,
  "MACD_12_26_9_macd": 1.4523,
  "MACD_12_26_9_macdsignal": 1.1850,
  "MACD_12_26_9_macdhist": 0.2673
}
```

---

## 1. Custom / Modern Indicators

Các chỉ báo này được xây dựng tối ưu hóa bằng NumPy mảng vector, giải quyết các nhu cầu phân tích kỹ thuật hiện đại mà TA-Lib chưa tích hợp sẵn:

| Tên Indicator | Aliases | Tham số mặc định | Đầu ra (Output Fields) | Mô tả & Ý nghĩa |
| :--- | :--- | :--- | :--- | :--- |
| **`VWAP`** | - | Không có | `vwap` | **Volume Weighted Average Price**: Giá bình quân gia quyền theo khối lượng giao dịch tích lũy. Thước đo giá trị công bằng chuẩn của các tổ chức quỹ lớn. |
| **`SUPERTREND`** | `SUPER_TREND` | `period`: 10<br>`multiplier`: 3.0 | `supertrend`: Đường SuperTrend<br>`trend`: Xu hướng (1=Bullish, -1=Bearish)<br>`upperband`<br>`lowerband` | **SuperTrend**: Chỉ báo bám sát xu hướng và làm dải Stop-loss động cực kỳ phổ biến trong giao dịch theo xu hướng. |
| **`ICHIMOKU`** | - | `tenkan_period`: 9<br>`kijun_period`: 26<br>`senkou_b_period`: 52 | `tenkan_sen`: Đường chuyển đổi<br>`kijun_sen`: Đường tiêu chuẩn<br>`senkou_span_a`: Mây A<br>`senkou_span_b`: Mây B | **Ichimoku Kinko Hyo (Mây Ichimoku)**: Đồ thị cái nhìn thoáng qua về cân bằng thị trường, xác định hỗ trợ/kháng cự động và động lượng giá. |
| **`KELTNER`** | `KC` | `period`: 20<br>`multiplier`: 2.0<br>`atr_period`: 10 | `upperband`<br>`middleband`<br>`lowerband` | **Keltner Channel**: Dải biến động dựa trên đường trung bình EMA kết hợp biên độ ATR. Hay dùng để bắt cú nén giá (Bollinger Squeeze). |
| **`PIVOT_POINTS`** | `PIVOT`, `PIVOTS` | Không có | `pivot`: Điểm xoay P<br>`r1`, `r2`, `r3`: Kháng cự<br>`s1`, `s2`, `s3`: Hỗ trợ | **Classic Pivot Points**: Các mốc đảo chiều hỗ trợ/kháng cự tính từ mức giá High, Low, Close của phiên trước. |
| **`HEIKIN_ASHI`** | `HA` | Không có | `ha_open`, `ha_high`, `ha_low`, `ha_close` | **Heikin-Ashi**: Kỹ thuật làm mượt nến Nhật loại bỏ độ nhiễu ngắn hạn, giúp nhìn xu hướng rõ ràng hơn. |

**Ví dụ Request Body:**
```json
{
  "indicators": [
    { "name": "VWAP" },
    { "name": "SUPERTREND", "parameters": { "period": 10, "multiplier": 3.0 } },
    { "name": "ICHIMOKU", "parameters": { "tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52 } },
    { "name": "KELTNER", "parameters": { "period": 20, "multiplier": 2.0, "atr_period": 10 } }
  ]
}
```

---

## 2. TA-Lib: Overlap Studies

Nhóm các chỉ báo đường xu hướng và dải trung bình giá (25 indicators):

| Tên Indicator | Tham số mặc định | Đầu ra | Mô tả |
| :--- | :--- | :--- | :--- |
| **`SMA`** | `timeperiod`: 30 *(hoặc `period`)* | `real` | Simple Moving Average (Đường trung bình động giản đơn) |
| **`EMA`** | `timeperiod`: 30 *(hoặc `period`)* | `real` | Exponential Moving Average (Đường trung bình hàm mũ) |
| **`WMA`** | `timeperiod`: 30 *(hoặc `period`)* | `real` | Weighted Moving Average (Đường trung bình trọng số) |
| **`DEMA`** | `timeperiod`: 30 | `real` | Double Exponential Moving Average (EMA kép giảm độ trễ) |
| **`TEMA`** | `timeperiod`: 30 | `real` | Triple Exponential Moving Average (EMA ba) |
| **`TRIMA`** | `timeperiod`: 30 | `real` | Triangular Moving Average (Trung bình tam giác) |
| **`KAMA`** | `timeperiod`: 30 | `real` | Kaufman Adaptive Moving Average (Trung bình thích ứng biến động) |
| **`MAMA`** | `fastlimit`: 0.5, `slowlimit`: 0.05 | `mama`, `fama` | MESA Adaptive Moving Average |
| **`T3`** | `timeperiod`: 5, `vfactor`: 0.7 | `real` | Triple Exponential Moving Average T3 của Tim Tillson |
| **`BBANDS`** | `timeperiod`: 20, `nbdevup`: 2.0, `nbdevdn`: 2.0, `matype`: 0 | `upperband`, `middleband`, `lowerband` | Bollinger Bands (Dải Bollinger) |
| **`SAR`** | `acceleration`: 0.02, `maximum`: 0.2 | `real` | Parabolic Stop and Reverse |
| **`SAREXT`** | `startvalue`: 0.0, `offsetonreverse`: 0.0, `accelerationinitlong`: 0.02, `accelerationlong`: 0.02, `accelerationmaxlong`: 0.2, ... | `real` | Parabolic SAR mở rộng đa tham số |
| **`DONCHIAN`** | `timeperiod`: 20 | `upperband`, `middleband`, `lowerband` | Donchian Channel (Kênh Donchian) |
| **`ACCBANDS`** | `timeperiod`: 20 | `upperband`, `middleband`, `lowerband` | Acceleration Bands (Dải gia tốc) |
| **`MIDPOINT`** | `timeperiod`: 14 | `real` | MidPoint qua một chu kỳ giá |
| **`MIDPRICE`** | `timeperiod`: 14 | `real` | Midpoint Price (Trung điểm giá High/Low) |
| **`HT_TRENDLINE`**| Không tham số | `real` | Hilbert Transform - Instantaneous Trendline |

---

## 3. TA-Lib: Momentum Indicators

Nhóm các chỉ báo đo lường sức mạnh và động lượng của xu hướng giá (47 indicators):

| Tên Indicator | Tham số mặc định | Đầu ra | Mô tả |
| :--- | :--- | :--- | :--- |
| **`RSI`** | `timeperiod`: 14 *(hoặc `period`)* | `real` | Relative Strength Index (Chỉ số sức mạnh tương đối) |
| **`MACD`** | `fastperiod`: 12, `slowperiod`: 26, `signalperiod`: 9 | `macd`, `macdsignal`, `macdhist` | Moving Average Convergence/Divergence |
| **`MACDEXT`**| `fastperiod`: 12, `fastmatype`: 0, `slowperiod`: 26, `slowmatype`: 0, `signalperiod`: 9, `signalmatype`: 0 | `macd`, `macdsignal`, `macdhist` | MACD tùy biến loại đường MA |
| **`MACDFIX`**| `signalperiod`: 9 | `macd`, `macdsignal`, `macdhist` | MACD tỷ lệ cố định (Fixed 12/26) |
| **`STOCH`** | `fastk_period`: 5, `slowk_period`: 3, `slowk_matype`: 0, `slowd_period`: 3, `slowd_matype`: 0 | `slowk`, `slowd` | Stochastic Oscillator |
| **`STOCHF`**| `fastk_period`: 5, `fastd_period`: 3, `fastd_matype`: 0 | `fastk`, `fastd` | Stochastic Fast |
| **`STOCHRSI`**| `timeperiod`: 14, `fastk_period`: 5, `fastd_period`: 3, `fastd_matype`: 0 | `fastk`, `fastd` | Stochastic RSI Oscillator |
| **`MOM`** | `timeperiod`: 10 | `real` | Momentum (Động lượng giá) |
| **`ROC`** | `timeperiod`: 10 | `real` | Rate of Change: `((price/prevPrice)-1)*100` |
| **`ROCR`** | `timeperiod`: 10 | `real` | Rate of Change ratio: `(price/prevPrice)` |
| **`ROCP`** | `timeperiod`: 10 | `real` | Rate of Change Percentage: `(price-prevPrice)/prevPrice` |
| **`CCI`** | `timeperiod`: 14 | `real` | Commodity Channel Index |
| **`ADX`** | `timeperiod`: 14 | `real` | Average Directional Movement Index (Độ mạnh xu hướng) |
| **`ADXR`** | `timeperiod`: 14 | `real` | Average Directional Movement Index Rating |
| **`APO`** | `fastperiod`: 12, `slowperiod`: 26, `matype`: 0 | `real` | Absolute Price Oscillator |
| **`PPO`** | `fastperiod`: 12, `slowperiod`: 26, `matype`: 0 | `real` | Percentage Price Oscillator |
| **`AROON`** | `timeperiod`: 14 | `aroondown`, `aroonup` | Aroon Oscillator |
| **`AROONOSC`**| `timeperiod`: 14 | `real` | Aroon Oscillator chênh lệch |
| **`BOP`** | Không tham số | `real` | Balance Of Power |
| **`WILLR`** | `timeperiod`: 14 | `real` | Williams' %R |
| **`ULTOSC`**| `timeperiod1`: 7, `timeperiod2`: 14, `timeperiod3`: 28 | `real` | Ultimate Oscillator |
| **`TRIX`** | `timeperiod`: 30 | `real` | 1-day Rate-Of-Change (ROC) của Triple Smooth EMA |
| **`MFI`** | `timeperiod`: 14 | `real` | Money Flow Index (Chỉ số dòng tiền kết hợp giá & volume) |
| **`PLUS_DI`**| `timeperiod`: 14 | `real` | Plus Directional Indicator (+DI) |
| **`MINUS_DI`**| `timeperiod`: 14 | `real` | Minus Directional Indicator (-DI) |
| **`PLUS_DM`**| `timeperiod`: 14 | `real` | Plus Directional Movement (+DM) |
| **`MINUS_DM`**| `timeperiod`: 14 | `real` | Minus Directional Movement (-DM) |
| **`DX`** | `timeperiod`: 14 | `real` | Directional Movement Index |
| **`CMO`** | `timeperiod`: 14 | `real` | Chande Momentum Oscillator |

---

## 4. TA-Lib: Volume Indicators

Nhóm các chỉ báo phân tích dòng tiền và khối lượng giao dịch (12 indicators):

| Tên Indicator | Tham số mặc định | Đầu ra | Mô tả |
| :--- | :--- | :--- | :--- |
| **`OBV`** | Không tham số | `real` | On Balance Volume (Khối lượng cân bằng lũy kế) |
| **`AD`** | Không tham số | `real` | Chaikin A/D (Accumulation/Distribution Line) |
| **`ADOSC`** | `fastperiod`: 3, `slowperiod`: 10 | `real` | Chaikin A/D Oscillator |
| **`CMF`** | `timeperiod`: 20 | `real` | Chaikin Money Flow (Dòng tiền Chaikin) |
| **`EFI`** | `timeperiod`: 13 | `real` | Elder's Force Index (Chỉ số lực của Alexander Elder) |
| **`MARKETFI`**| Không tham số | `real` | Market Facilitation Index |

---

## 5. TA-Lib: Volatility Indicators

Nhóm các chỉ báo đo lường mức độ biến động thị trường (7 indicators):

| Tên Indicator | Tham số mặc định | Đầu ra | Mô tả |
| :--- | :--- | :--- | :--- |
| **`ATR`** | `timeperiod`: 14 *(hoặc `period`)* | `real` | Average True Range (Biên độ dao động thực tế bình quân) |
| **`NATR`** | `timeperiod`: 14 | `real` | Normalized Average True Range (ATR chuẩn hóa phần trăm) |
| **`TRANGE`** | Không tham số | `real` | True Range (Biên độ thực tế từng phiên) |
| **`ADR`** | `timeperiod`: 14 | `real` | Average Daily Range |
| **`CVI`** | `timeperiod`: 14 | `real` | Chaikin's Volatility |
| **`MASSI`** | `fastperiod`: 9, `slowperiod`: 25 | `real` | Mass Index |

---

## 6. TA-Lib: Pattern Recognition (Mô hình nến Nhật)

Nhóm phát hiện 61 mẫu hình nến Nhật đảo chiều và tiếp diễn. 
- **Giá trị trả về**:
  - `100`: Tín hiệu Bullish (Tăng giá mạnh)
  - `-100`: Tín hiệu Bearish (Giảm giá mạnh)
  - `0`: Không xuất hiện mô hình

### Danh sách mô hình phổ biến & Tên gọi tắt (Aliases):
| Tên Chuẩn TA-Lib | Tên gọi tắt (Alias) | Mô tả mẫu hình |
| :--- | :--- | :--- |
| `CDLDOJI` | **`DOJI`** | Nến Doji (Giá mở cửa xấp xỉ giá đóng cửa) |
| `CDLHAMMER` | **`HAMMER`** | Nến Búa Hammer (Tín hiệu đảo chiều tăng) |
| `CDLENGULFING` | **`ENGULFING`** | Nến Nhấn chìm (Engulfing Bullish/Bearish) |
| `CDLMORNINGSTAR` | **`MORNING_STAR`** | Nến Sao mai (Morning Star - Đảo chiều đáy) |
| `CDLEVENINGSTAR` | **`EVENING_STAR`** | Nến Sao hôm (Evening Star - Đảo chiều đỉnh) |
| `CDLSHOOTINGSTAR`| **`SHOOTING_STAR`** | Nến Sao băng (Bóng nến trên dài) |
| `CDLHANGINGMAN` | **`HANGING_MAN`** | Nến Người treo cổ |
| `CDLHARAMI` | **`HARAMI`** | Nến Mẹ bồng con (Harami Pattern) |
| `CDLMARUBOZU` | **`MARUBOZU`** | Nến Marubozu (Thân nến đặc không có râu) |
| `CDLINVERTEDHAMMER`| **`INVERTED_HAMMER`** | Nến Búa ngược |
| `CDLSPINNINGTOP` | **`SPINNING_TOP`** | Nến Con xoay (Spinning Top) |
| `CDL3WHITESOLDIERS`| **`THREE_WHITE_SOLDIERS`** | Ba chàng lính trắng (3 nến tăng liên tiếp) |
| `CDL3BLACKCROWS` | **`THREE_BLACK_CROWS`** | Ba con quạ đen (3 nến giảm liên tiếp) |
| `CDLDRAGONFLYDOJI`| **`DRAGONFLY_DOJI`** | Nến Doji Chuồn chuồn |
| `CDLGRAVESTONEDOJI`| **`GRAVESTONE_DOJI`** | Nến Doji Bia mộ |

*(Ngoài ra hỗ trợ đầy đủ 46 mẫu hình nến khác: `CDL2CROWS`, `CDL3INSIDE`, `CDL3LINESTRIKE`, `CDLADVANCEBLOCK`, `CDLBELTHOLD`, `CDLBREAKAWAY`, `CDLDARKCLOUDCOVER`, `CDLPIERCING`, `CDLTRISTAR`, v.v.)*

---

## 7. TA-Lib: Price Transform

Nhóm biến đổi các mức giá OHLC (6 indicators):

| Tên Indicator | Đầu ra | Công thức / Ý nghĩa |
| :--- | :--- | :--- |
| **`AVGPRICE`** | `real` | `(Open + High + Low + Close) / 4` |
| **`MEDPRICE`** | `real` | `(High + Low) / 2` (Giá trung vị) |
| **`TYPPRICE`** | `real` | `(High + Low + Close) / 3` (Typical Price) |
| **`WCLPRICE`** | `real` | `(High + Low + 2 * Close) / 4` (Weighted Close Price) |

---

## 8. TA-Lib: Statistic Functions

Nhóm hàm thống kê và hồi quy tuyến tính (11 indicators):

| Tên Indicator | Tham số mặc định | Đầu ra | Mô tả |
| :--- | :--- | :--- | :--- |
| **`LINEARREG`** | `timeperiod`: 14 | `real` | Linear Regression (Đường hồi quy tuyến tính) |
| **`LINEARREG_SLOPE`**| `timeperiod`: 14 | `real` | Hệ số góc hồi quy tuyến tính (Đo độ dốc xu hướng) |
| **`LINEARREG_ANGLE`**| `timeperiod`: 14 | `real` | Góc của đường hồi quy tuyến tính (tính bằng độ) |
| **`LINEARREG_INTERCEPT`**| `timeperiod`: 14 | `real` | Điểm chặn đường hồi quy tuyến tính |
| **`STDDEV`** | `timeperiod`: 5, `nbdev`: 1.0 | `real` | Standard Deviation (Độ lệch chuẩn) |
| **`VAR`** | `timeperiod`: 5, `nbdev`: 1.0 | `real` | Variance (Phương sai) |
| **`TSF`** | `timeperiod`: 14 | `real` | Time Series Forecast |
| **`CORREL`** | `timeperiod`: 30 | `real` | Pearson's Correlation Coefficient |
| **`BETA`** | `timeperiod`: 30 | `real` | Hệ số Beta đo độ nhạy thị trường |

---

## 9. TA-Lib: Cycle Indicators

Nhóm phân tích chu kỳ sóng Hilbert Transform (5 indicators):

| Tên Indicator | Đầu ra | Mô tả |
| :--- | :--- | :--- |
| **`HT_DCPERIOD`** | `real` | Hilbert Transform - Dominant Cycle Period |
| **`HT_DCPHASE`** | `real` | Hilbert Transform - Dominant Cycle Phase |
| **`HT_PHASOR`** | `inphase`, `quadrature` | Hilbert Transform - Phasor Components |
| **`HT_SINE`** | `sine`, `leadsine` | Hilbert Transform - SineWave |
| **`HT_TRENDMODE`**| `real` | Hilbert Transform - Trend vs Cycle Mode |
