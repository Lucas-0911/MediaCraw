# Hướng dẫn chạy và dùng WebUI

Handbook đầy đủ (mọi lối vào, không chỉ UI): [handbook/usage.md](handbook/usage.md). Kiến trúc: [handbook/architecture.md](handbook/architecture.md).

WebUI cấu hình crawler, xem log realtime, duyệt file dữ liệu, và chạy **Trend Radar** (xếp hạng sản phẩm hot TQ + Telegram). Backend FastAPI spawn subprocess `uv run python main.py`; frontend React nhận log qua WebSocket.

Màn hình chính mặc định là tab **TREND_RADAR**. Ngôn ngữ mặc định: **tiếng Việt** (VI / EN). Người vận hành tự chịu trách nhiệm về điều khoản nền tảng và dữ liệu. License: [LICENSE](../LICENSE).

---

## 1. Chuẩn bị

| Mục | Yêu cầu |
|-----|---------|
| Python | 3.11, quản lý bằng [uv](https://docs.astral.sh/uv/getting-started/installation) |
| Node.js | `>= 16` (frontend + Douyin/Zhihu) |
| Playwright | `uv run playwright install` |
| Chrome/Edge | Khuyến nghị bản `>= 144` nếu dùng CDP (mặc định trong `config/base_config.py`) |

Từ thư mục gốc dự án:

```bash
uv sync
uv run playwright install
cd webui && npm install
```

---

## 2. Khởi động

### Cách A — Dev (khuyến nghị khi chỉnh UI)

Mở **hai terminal**:

```bash
# Terminal 1 — API :8080
uv run uvicorn api.main:app --port 8080 --reload
```

```bash
# Terminal 2 — Vite :5173, proxy /api (kể cả WebSocket) sang :8080
cd webui
npm run dev
```

Mở **http://localhost:5173/**

Vite phải chạy cùng lúc với API. Nếu chỉ mở frontend, bước kiểm tra môi trường sẽ fail.

### Cách B — Một process (API phục vụ UI đã build)

```bash
cd webui
npm run build          # output: api/webui/
cd ..
uv run uvicorn api.main:app --port 8080
```

Mở **http://localhost:8080/**

Nếu chưa build, `/` chỉ trả JSON: *WebUI not found, please build it first*.

Lệnh tương đương: `uv run python -m api.main` (cũng lắng nghe `:8080`).

---

## 3. Lần đầu mở UI

Không có modal license học tập. Chỉ còn:

1. **Environment check** — gọi `GET /api/env/check` (chạy `uv run main.py --help`). Thành công thì đóng sau ~1,5 giây. Fail thì xem lỗi hoặc **Skip**.
2. Màn hình chính: tab **TREND_RADAR** (mặc định) rồi **CRAWL**.

Đổi ngôn ngữ (VI / EN) và theme ở góc phải header.

---

## 4. Bố cục màn hình

```
┌──────────────────────────────────────────────────────────────┐
│ Header: Trend Radar · trạng thái · theme · language          │
├──────────────────────────────────────────────────────────────┤
│ Tabs: TREND_RADAR | CRAWL                                    │
│ TREND_RADAR: toolbar scheduler · lọc SP · bảng · chi tiết    │
│              (cổng OK/NO, snapshot t0/t1, video, listing)    │
│              lịch sử Telegram · settings gom nhóm            │
│ CRAWL: TARGET_MATRIX · AUTH · OUTPUT · BẮT ĐẦU CRAWL         │
├──────────────────────────────────────────────────────────────┤
│ Terminal log (popup sau BẮT ĐẦU CRAWL)                       │
└──────────────────────────────────────────────────────────────┘
```

WebUI **không** crawler trong trình duyệt. Nút Start gửi `POST /api/crawler/start`; `CrawlerManager` ghép argv rồi Popen CLI. Log stdout hiện realtime qua `/api/ws/logs`.

---

## 5. Cấu hình và chạy (tab CRAWL)

Mặc định trên UI: nền tảng **Douyin**, mode **search**, login **QR**, lưu **jsonl**, bật comment, không headless. Số bài `max_notes_count` mặc định 15, số comment/bài `max_comments_count` mặc định 10 — cả hai được gửi lên API.

Douyin là nguồn nhiệt chính. Khi chọn Douyin, UI gợi ý keyword ngành tiếng Trung (ví dụ `美白精华`) và nhắc bật comment để cổng intent mua hoạt động.

### Cột TARGET_MATRIX

| Mục | Ý nghĩa |
|-----|---------|
| PLATFORM | `xhs` Xiaohongshu · `dy` Douyin · `ks` Kuaishou · `bili` Bilibili · `wb` Weibo · `tieba` Tieba · `zhihu` Zhihu · `tiktok` TikTok VN |
| CRAWL_TYPE | `search` / `detail` / `creator` |
| START_PAGE | Trang bắt đầu (search) |
| SỐ BÀI | `max_notes_count` — số video/bài tối đa mỗi lần crawl |
| SỐ COMMENT/BÀI | `max_comments_count` — số comment tối đa mỗi bài |

**Search** — gõ từ khóa, Enter để thêm tag. Nhiều từ khóa được ghép bằng dấu phẩy khi gửi API.

**Detail** — dán ID hoặc URL bài/video, mỗi dòng một mục (hoặc cách nhau bằng dấu phẩy). UI parse sẵn:

| Nền tảng | Ví dụ |
|----------|--------|
| Bilibili | `BV1xxxx` hoặc `https://www.bilibili.com/video/BV1xxxx` |
| Xiaohongshu | URL đầy đủ **phải có `xsec_token`** |
| Douyin | ID số, `/video/xxx`, hoặc short link `v.douyin.com` |
| Weibo | ID số hoặc URL weibo |
| Kuaishou | ID short-video hoặc URL |

**Creator** — ID/URL trang tác giả. Xiaohongshu: URL profile cũng cần `xsec_token`.

### Cột AUTH_MATRIX

UI chỉ expose hai kiểu (API `/api/config/options`):

| LOGIN_METHOD | Khi nào dùng |
|--------------|----------------|
| QR Code | Mặc định. Để `HEADLESS` tắt, quét mã trên cửa sổ Chrome/CDP. |
| Cookie | Dán chuỗi cookie. Xiaohongshu/Douyin dễ kẹt slider — không khuyến nghị. |

Đăng nhập SĐT không có trên WebUI; dùng CLI `--lt phone` (xem [phone-login.md](phone-login.md)).

CDP mặc định trong `config/base_config.py` (`ENABLE_CDP_MODE=True`, `CDP_CONNECT_EXISTING=True`). Lần đầu Chrome có thể hiện hộp xác nhận remote debug — bấm Accept. Chi tiết: [cdp-mode.md](cdp-mode.md).

### Cột OUTPUT_CONFIG

| Mục | Giá trị trên UI |
|-----|-----------------|
| SAVE_FORMAT | jsonl · json · csv · excel · sqlite · MySQL (`db`) · mongodb |
| Comment Extraction | Crawl comment cấp 1 |
| Sub-comments | Comment cấp 2 (chỉ khi đã bật comment) |
| HEADLESS_MODE | Ẩn cửa sổ trình duyệt — tắt nếu cần quét QR / qua captcha |

SQLite/MySQL: CLI tự `init_db` khi start. MySQL cần tạo DB và sửa `config/db_config.py` trước. Xem [data_storage_guide.md](data_storage_guide.md).

PostgreSQL có trên CLI (`--save_data_option postgres`) nhưng **không** có trong dropdown WebUI.

### Chạy / dừng

1. Điền cấu hình.
2. **BẮT ĐẦU CRAWL** — log hiện ở terminal popup. Header có badge đang chạy.
3. **DỪNG** — gửi SIGTERM, chờ tối đa ~15 giây, rồi SIGKILL nếu chưa thoát.
4. Chỉ một crawler tại một thời điểm. Start khi đang chạy → HTTP 400.

File kết quả mặc định trong `data/{platform}/`. Trend Radar ghi `data/trend.sqlite`.

---

## 6. Tab TREND_RADAR

Đây là màn chính. Luồng:

1. Crawl Douyin (và/hoặc TikTok) ở tab CRAWL, bật comment nếu dùng cổng intent.
2. Mở TREND_RADAR: toolbar hiện `last_run` / `last_result` từ `GET /api/trend/scheduler`.
3. Lọc bảng: tìm tên, nhãn (QUAN SAT / DANG HOT / DU KIEN NONG), `min_confidence` gọi `GET /api/trend/products`.
4. Click một SP để xem chi tiết (không dump JSON):
   - Cổng badge **OK/NO**: mention+spread, play còn tăng, intent mua, trends CN, định danh SKU/tên.
   - Snapshot **t0** (cũ) và **t1** (mới): HeatNow, play_vel, mention, spread, intent, trends_CN.
   - Video: play, like, tuổi, URL, path mp4 nếu có.
   - Listing Shopee/Lazada + đường dẫn CSV draft.
   - Nút **TÌM SHOPEE/LAZADA** / **TẢI MP4**.
5. Khối **lịch sử Telegram**: `GET /api/trend/alerts`.
6. Settings gom nhóm (ghi `data/trend_settings.json`):
   - Quét: interval, cron, gap snapshot, cooldown, bật scheduler.
   - Video: số clip/alert, tuổi min/max, require play tăng, max mp4, tải mp4 khi score.
   - Ngưỡng: confidence, mention, spread, intent, name videos, HeatNow hot/rising.
   - Telegram: token, chat id + **GỬI THỬ** (`POST /api/trend/telegram/test`).
   - LLM: enabled, base URL, model, API key.
   - Marketplace: Shopee, Lazada, Google Trends CN, platforms/keywords radar.
7. **LƯU CẤU HÌNH** → `PUT /api/trend/settings`. **CHẤM ĐIỂM** → `POST /api/trend/scan`.
8. Lần score đầu = snapshot. Lần sau `TREND_SNAPSHOT_GAP_HOURS` mới Telegram nếu Confidence đủ.

API: `GET /api/trend/products`, `GET /api/trend/products/{key}`, `GET /api/trend/alerts`, `GET /api/trend/scheduler`, `PUT /api/trend/settings`, `POST /api/trend/scan`, `POST /api/trend/telegram/test`.

---

## 7. Terminal và Data Explorer

- Log tự cuộn xuống; giữ tối đa ~500 dòng.
- Xóa log: icon thùng rác. Khôi phục: icon refresh (reload trang).
- Thu gọn terminal bằng chevron trên header console.
- **Data Explorer** (nút trên thanh terminal): liệt kê file `.json` / `.csv` / `.xlsx` trong `data/`, preview, tải về. JSONL **không** nằm trong danh sách API hiện tại — nếu chọn jsonl, xem file trực tiếp trong thư mục `data/`.

---

## 8. Luồng điển hình (Douyin search + QR + radar)

1. Khởi động API + Vite (cách A).
2. Mở http://localhost:5173 — kiểm tra môi trường, vào thẳng TREND_RADAR.
3. Tab CRAWL: PLATFORM = Douyin, CRAWL_TYPE = search, thêm keyword ngành Trung, Enter.
4. LOGIN = QR, HEADLESS tắt, SAVE = jsonl, comment bật, chỉnh số bài/comment nếu cần.
5. BẮT ĐẦU CRAWL.
6. Quét QR trên cửa sổ trình duyệt (hoặc Accept CDP nếu Chrome hỏi).
7. Quay lại TREND_RADAR → CHẤM ĐIỂM. Lần sau đủ gap snapshot mới Telegram.
8. Điền bot token / chat id, bấm GỬI THỬ trước khi bật scheduler.

TikTok VN: guest mặc định, từ khóa tiếng Việt. Xiaohongshu detail/creator nhớ copy URL đủ `xsec_token`.

---

## 9. Sự cố thường gặp

| Hiện tượng | Việc cần làm |
|------------|----------------|
| Env check fail / *uv command not found* | Cài uv, thêm vào PATH, API phải chạy từ thư mục gốc dự án |
| Frontend :5173 nhưng API chết | Mở terminal 1: `uv run uvicorn api.main:app --port 8080` |
| `:8080` chỉ JSON, không UI | `cd webui && npm run build` rồi restart uvicorn |
| QR không hiện / slider kẹt | Tắt headless; dùng CDP + Chrome thật; xem [faq.md](faq.md) |
| `Cannot connect to existing browser on port 9222` | Bật remote debug Chrome, hoặc `CDP_CONNECT_EXISTING = False` |
| Start báo crawler already running | DỪNG trước, hoặc kill process `main.py` cũ |
| Cookie Xiaohongshu/Douyin fail | Đổi QR + CDP; cookie dễ dính captcha |
| Không thấy file jsonl trên Data Explorer | API list chỉ json/csv/xlsx — mở `data/` trên đĩa |
| Douyin/Zhihu lỗi execjs / thiếu `;` | Cài Node.js `>= 16` |
| GỬI THỬ Telegram fail | Token/chat id trống hoặc bot chưa được start trong chat |

API docs (Swagger) khi server chạy: http://localhost:8080/docs

Health: `GET http://localhost:8080/api/health`

---

## 10. WebUI điều khiển những gì

WebUI map sang CLI:

```text
uv run python main.py
  --platform ...
  --lt qrcode|cookie
  --type search|detail|creator
  --save_data_option ...
  --keywords / --specified_id / --creator_id
  --start
  --get_comment / --get_sub_comment
  --cookies
  --headless
  --crawler_max_notes_count
  --max_comments_count_singlenotes
```

Không chỉnh được từ UI (vẫn lấy từ `config/base_config.py`): CDP, proxy IP, concurrency, crawl media, wordcloud, `XHS_INTERNATIONAL`, v.v. Sửa file config rồi start lại từ UI.

Trend Radar settings chỉnh trên tab TREND_RADAR (và/hoặc `data/trend_settings.json` / env).

---

## 11. Tắt máy an toàn

1. DỪNG trên UI nếu crawler đang chạy.
2. Ctrl+C Vite, rồi Ctrl+C uvicorn.
3. CDP: `AUTO_CLOSE_BROWSER` trong config quyết định có đóng Chrome khi process CLI thoát hay không.
