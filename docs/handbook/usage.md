# Hướng dẫn sử dụng Trend Radar

Đối tượng: người vận hành. Kiến trúc từng package: [architecture.md](architecture.md). UI chi tiết: [webui-guide.md](../webui-guide.md).

Người vận hành tự chịu trách nhiệm về điều khoản nền tảng, dữ liệu và cách dùng. License: [LICENSE](../../LICENSE). Nguồn crawler: [NOTICE](../../NOTICE).

---

## 1. Sản phẩm làm gì / không làm gì

### Làm

1. Crawl Douyin (và tùy chọn TikTok VN) theo keyword ngành.
2. Nhận diện SKU (小黄车 / `product_id`) hoặc tên lặp trên nhiều video.
3. Chấm **HeatNow** + **Confidence 0–5** trên **hai snapshot** (khoảng cách cấu hình được).
4. Gửi Telegram khi `Confidence >= TREND_MIN_CONFIDENCE` (mặc định 4): tên SP, breakdown công thức, N video.
5. Tùy chọn: LLM gợi ý tên, tải mp4, draft listing Shopee/Lazada.

```text
HeatNow = 0.35 play_velocity
        + 0.20 eng_velocity
        + 0.20 mention
        + 0.15 spread
        + 0.10 intent_wilson
```

Google Trends `geo=CN` là cổng xác nhận riêng, **không** cộng vào HeatNow. Trọng số và ngưỡng: `config/trend_config.py`, biến môi trường, hoặc form Trend settings trên WebUI (`data/trend_settings.json`).

| Cổng HeatNow | Ý nghĩa |
|--------------|---------|
| play_velocity | Lượt xem / tuổi clip (giờ), lấy median |
| eng_velocity | (like + comment + share) / tuổi |
| mention | Số video gắn cùng sản phẩm |
| spread | Số creator khác nhau (`creator_hash`) |
| intent_wilson | Wilson lower bound trên comment “muốn mua” |

### Không làm

- Scrape 蝉妈妈 / 飞瓜 / FastMoss / Kalodata
- Thanh toán Shopee/Lazada tự động (OTP / 2FA / captcha)
- `TREND_ORDER_MODE` mặc định `draft` — chỉ link/search, không checkout

### Nền tảng crawl

| Nền tảng | Mã CLI | Search | Detail | Comment | Ingest Trend Radar |
|----------|--------|--------|--------|---------|--------------------|
| Douyin | `dy` | có | có | có | nguồn nhiệt chính |
| TikTok VN | `tiktok` | có | có | có | nguồn phụ |
| Xiaohongshu | `xhs` | có | có | có | không chấm heat SP TQ |
| Kuaishou | `ks` | có | có | có | không |
| Bilibili | `bili` | có | có | có | không |
| Weibo | `wb` | có | có | có | không |
| Baidu Tieba | `tieba` | có | có | có | không |
| Zhihu | `zhihu` | có | có | có | không |

---

## 2. Cài đặt

- Python 3.11 + [uv](https://docs.astral.sh/uv/getting-started/installation)
- Node.js >= 16 (WebUI; một số nền tảng cần JS runtime)
- Chrome >= 144 nếu dùng CDP (mặc định)

Package Python: `trendradar` trong `pyproject.toml`. `uv` quản lý dependency; `requirements.txt` là legacy.

```bash
uv sync
uv run playwright install   # chỉ khi KHÔNG dùng CDP
cd webui && npm install
```

CDP (mặc định `ENABLE_CDP_MODE = True`, `CDP_CONNECT_EXISTING = True`):

1. Mở Chrome, vào `chrome://inspect/#remote-debugging`
2. Allow remote debugging
3. Cổng `127.0.0.1:9222` (`CDP_DEBUG_PORT`)
4. Lần đầu Chrome có thể hỏi xác nhận — Accept

Tắt CDP: `ENABLE_CDP_MODE = False` trong `config/base_config.py`. Chi tiết: [cdp-mode.md](../cdp-mode.md). Môi trường local: [local-environment.md](../local-environment.md).

---

## 3. Chọn lối vào

| Lối vào | Lệnh / URL | Khi dùng |
|---------|------------|----------|
| WebUI (khuyến nghị) | `:5173` dev hoặc `:8080` build | Vận hành hàng ngày: TREND_RADAR + CRAWL |
| CLI crawler | `uv run python main.py …` | Script, debug một nền tảng; cũng là subprocess WebUI/Agent |
| HTTP API / Swagger | http://localhost:8080/docs | Tích hợp, RUN_SCORE, scheduler |
| Telegram hội thoại | Bot inbound | Chat thường → Agent; slash `/status` `/crawl` → handler cũ |
| Telegram alert | `trend/alerts.py` | Một chiều khi đủ Confidence — **không** phải bot chat |

Hợp đồng bất biến: crawler **luôn** là process `uv run python main.py`. WebUI/API/Agent không crawl in-process.

---

## 4. WebUI

### 4.1 Khởi động

Hai process (dev):

```bash
# Terminal 1
uv run uvicorn api.main:app --port 8080 --reload

# Terminal 2
cd webui && npm run dev
```

Mở http://localhost:5173/ — Vite phải chạy **cùng** API, không thì bước env check fail.

Một process:

```bash
cd webui && npm run build    # output: api/webui/
uv run uvicorn api.main:app --port 8080
```

Mở http://localhost:8080/. Chưa build thì `/` trả JSON *WebUI not found*.

Tương đương: `uv run python -m api.main`.

### 4.2 Lần đầu mở

1. **Environment check** — `GET /api/env/check` chạy `uv run main.py --help`. Thành công thì đóng ~1,5s. Fail: xem lỗi hoặc Skip.
2. Tab mặc định **TREND_RADAR**, cạnh đó **CRAWL**.
3. Ngôn ngữ VI / EN (và ZH trong locale), theme góc phải.

Không có modal license học tập.

### 4.3 Tab TREND_RADAR

- Bảng sản phẩm (lọc min Confidence)
- Chi tiết: cổng OK/NO, snapshot t0/t1, video, listing
- Form settings: chu kỳ quét, số video/alert, Telegram token/chat, LLM, tải mp4, marketplace, scheduler
- **RUN_SCORE** = `POST /api/trend/scan`
- Bật/tắt scheduler = `POST /api/trend/scheduler/start|stop`
- Draft Shopee/Lazada, tải mp4 theo `product_key`
- Lịch sử alert Telegram

### 4.4 Tab CRAWL

Mặc định UI: Douyin, search, QR, jsonl, bật comment, không headless. `max_notes_count` 15, `max_comments_count` 10.

| Cột | Việc |
|-----|------|
| TARGET_MATRIX | Platform, type, start page, số bài, số comment, keyword/ID |
| AUTH | QR (mặc định) hoặc Cookie. Phone **không** có trên UI |
| OUTPUT | jsonl/json/csv/excel/sqlite/MySQL/mongodb, comment, sub-comment, headless |

Nút Start → `POST /api/crawler/start`. Một crawler tại một thời điểm; trùng → HTTP 400. Log realtime popup qua `ws://…/api/ws/logs`.

Douyin: dùng keyword tiếng Trung (ví dụ `美白精华`). Bật comment nếu cần cổng intent mua.

**Search** — tag keyword, ghép bằng dấu phẩy.

**Detail** — ID hoặc URL, mỗi dòng một mục:

| Nền tảng | Ví dụ |
|----------|--------|
| Bilibili | `BV1xxxx` hoặc URL `/video/BV1xxxx` |
| Xiaohongshu | URL **phải có** `xsec_token` |
| Douyin | ID số, `/video/xxx`, short link `v.douyin.com` |
| Weibo / Kuaishou | ID hoặc URL |

**Creator** — ID/URL trang tác giả. Xiaohongshu profile cũng cần `xsec_token`.

Data explorer duyệt JSON/CSV/Excel dưới `data/` (`GET /api/data/files`). JSONL mặc định **không** luôn hiện trong explorer (API chỉ liệt `.json` `.csv` `.xlsx`).

Chi tiết từng control: [webui-guide.md](../webui-guide.md).

### 4.5 Luồng operator Trend Radar

1. Điền Trend settings. Token: `TREND_TELEGRAM_BOT_TOKEN` + `TREND_TELEGRAM_CHAT_ID` (env hoặc form).
2. Crawl Douyin keyword tiếng Trung, bật comment. Lần 1 chỉ snapshot — nhãn **QUAN SAT**.
3. Chờ `TREND_SNAPSHOT_GAP_HOURS` (mặc định 6h).
4. Crawl/score lại. Telegram **chỉ** khi Confidence đủ **và** đã có 2 snapshot.
5. RUN_SCORE thủ công hoặc bật scheduler.

Kiểm tra bot: `POST /api/trend/telegram/test`.

---

## 5. CLI crawler

```bash
uv run main.py --help
uv run main.py --platform dy --lt qrcode --type search --keywords "美白精华"
uv run main.py --platform tiktok --lt qrcode --type search --keywords "skincare"
```

Alias: `uv run python -m app.cli` vẫn chạy `main`.

### Flag

| Flag | Ý nghĩa | Nguồn default |
|------|---------|----------------|
| `--platform` | `xhs` `dy` `ks` `bili` `wb` `tieba` `zhihu` `tiktok` | `config.PLATFORM` |
| `--lt` | `qrcode` `phone` `cookie` | `LOGIN_TYPE` |
| `--type` | `search` `detail` `creator` | `CRAWLER_TYPE` |
| `--keywords` | Keyword, cách nhau bằng dấu phẩy | `KEYWORDS` |
| `--specified_id` | ID/URL mode detail | platform config |
| `--creator_id` | ID/URL mode creator | platform config |
| `--start` | Trang bắt đầu | `START_PAGE` |
| `--crawler_max_notes_count` | Số bài/video tối đa | `CRAWLER_MAX_NOTES_COUNT` |
| `--get_comment` / `--get_sub_comment` | yes/true/1 hoặc no | `ENABLE_GET_*` |
| `--max_comments_count_singlenotes` | Comment cấp 1 mỗi bài | |
| `--headless` | Ẩn cửa sổ (Playwright và CDP) | `HEADLESS` |
| `--save_data_option` | csv json jsonl sqlite db mongodb excel postgres | `SAVE_DATA_OPTION` (jsonl) |
| `--save_data_path` | Thư mục gốc; trống = `data/` | |
| `--cookies` | Chuỗi cookie khi `--lt cookie` | |
| `--init_db` | `sqlite` `mysql` `postgres` — tạo bảng | |
| `--enable_ip_proxy` | Bật pool | |
| `--ip_proxy_provider_name` | `kuaidaili` `wandouhttp` `static` | |
| `--static_proxy_url` | `http://user:pass@host:port` | |
| `--max_concurrency_num` | Concurrent | `MAX_CONCURRENCY_NUM` |

CLI ghi đè `config.*` cho process hiện tại, không sửa file.

Phone login: `--lt phone` — không khuyến nghị; xem [phone-login.md](../phone-login.md).

Dữ liệu crawl: `data/{platform}/`. Radar: `data/trend.sqlite`.

---

## 6. HTTP API

Base: http://localhost:8080 — Swagger `/docs`.

### Crawler

| Method | Path | Việc |
|--------|------|------|
| POST | `/api/crawler/start` | Body `CrawlerStartRequest`. Fail nếu đã chạy → 400 |
| POST | `/api/crawler/stop` | Dừng process |
| GET | `/api/crawler/status` | `idle` `running` `stopping` `error` |
| GET | `/api/crawler/logs?limit=100` | Log ring |

### Data

| Method | Path | Việc |
|--------|------|------|
| GET | `/api/data/files` | JSON/CSV/Excel dưới `data/` |
| GET | `/api/data/…` | Preview / download (xem router) |

### WebSocket

| Path | Việc |
|------|------|
| `/api/ws/logs` | stdout crawler |
| `/api/ws/status` | Đổi status |

### Trend

| Method | Path | Việc |
|--------|------|------|
| GET/PUT | `/api/trend/settings` | GET mask secret; PUT ghi `data/trend_settings.json` |
| GET | `/api/trend/products?min_confidence=` | Bảng SP |
| GET | `/api/trend/products/{product_key}` | SP + videos + snapshots + listings |
| GET | `/api/trend/alerts` | Lịch sử Telegram |
| POST | `/api/trend/scan` | `process_scan()` — score + optional alert/media/marketplace |
| GET | `/api/trend/scheduler` | Trạng thái vòng nền |
| POST | `/api/trend/scheduler/start` | Bật `TREND_SCHEDULER_ENABLED` |
| POST | `/api/trend/scheduler/stop` | Tắt |
| POST | `/api/trend/products/{key}/marketplace` | Draft Shopee/Lazada |
| POST | `/api/trend/products/{key}/media` | Tải mp4 |
| POST | `/api/trend/telegram/test` | Gửi “Trend Radar test” |

### Health

`GET /api/health` → `{ "status": "ok" }`.  
`GET /api/env/check` → chạy `uv run main.py --help` timeout 30s.

CORS chỉ localhost:5173 và :3000.

---

## 7. Telegram — hai đường

### 7.1 Outbound alert (Trend Radar)

Cấu hình `TREND_TELEGRAM_BOT_TOKEN` + `TREND_TELEGRAM_CHAT_ID`. `trend/alerts.py` POST Bot API. Nội dung: label, Confidence, HeatNow, cổng OK/NO, công thức, N video, listing draft.

Token này **không** cho user chat quyền đọc data hay start crawler.

### 7.2 Inbound Agent

`channels/telegram/adapter.py`:

- Tin bắt đầu `/` → handler slash cũ.
- Tin thường → `AgentLoop` + memory.

Cấu hình Agent (`config/agent_config.py` hoặc env):

| Biến | Default | Ý nghĩa |
|------|---------|---------|
| `AGENT_LLM_ENABLED` | false | Bật LLM; tắt thì không gọi HTTP LLM |
| `AGENT_LLM_BASE_URL` | OpenAI compatible | |
| `AGENT_LLM_MODEL` | `gpt-4o-mini` | |
| `AGENT_LLM_API_KEY` | trống | Không nhét vào `AgentContext` |
| `MAX_AGENT_STEPS` | 4 | Số vòng tool |
| `AGENT_REQUEST_TIMEOUT_SECONDS` | 45 | |
| `AGENT_TOOL_TIMEOUT_SECONDS` | 10 | |
| `AGENT_MEMORY_MAX_MESSAGES` | 20 | History đưa vào LLM |
| `AGENT_CONTEXT_TTL` | 3600 | Short-term state |
| `AGENT_MEMORY_CACHE_TYPE` | `memory` | hoặc `redis` |
| `AGENT_MEMORY_DB_TYPE` | `sqlite` | |
| `AGENT_MEMORY_SQLITE_PATH` | `database/agent_memory.db` | Độc lập crawler store |

Quyền tool (resolver gắn vào context):

- `search_crawl_results` cần `crawl_results:read` — chỉ tìm file đã crawl.
- `crawl_platform` cần `crawler:run` **và** quota > 0 — user phải **nói rõ** muốn crawl. Prompt cấm start crawler khi chỉ hỏi “mới nhất”.

User chưa `authenticated` hoặc `license != active` → tool DENIED. Policy chặn SQL/shell dù LLM yêu cầu.

Wiring: `app/wiring.py` `build_telegram_handler`.

---

## 8. Catalog cấu hình

### 8.1 Crawler — `config/base_config.py`

| Biến | Default | Ý nghĩa |
|------|---------|---------|
| `PLATFORM` | `xhs` | Mã nền tảng |
| `KEYWORDS` | | Keyword, dấu phẩy |
| `LOGIN_TYPE` | `qrcode` | qrcode / phone / cookie |
| `CRAWLER_TYPE` | `search` | search / detail / creator |
| `HEADLESS` | False | Mở cửa sổ — cần để quét QR |
| `SAVE_LOGIN_STATE` | True | Giữ user data dir |
| `ENABLE_CDP_MODE` | True | Chrome local |
| `CDP_DEBUG_PORT` | 9222 | |
| `CDP_CONNECT_EXISTING` | True | Gắn Chrome đang mở |
| `AUTO_CLOSE_BROWSER` | True | |
| `SAVE_DATA_OPTION` | `jsonl` | csv json jsonl sqlite db mongodb excel postgres |
| `SAVE_DATA_PATH` | `""` | Trống = `data/` |
| `CRAWLER_MAX_NOTES_COUNT` | 15 | |
| `MAX_CONCURRENCY_NUM` | 1 | |
| `ENABLE_GET_COMMENTS` | True | Cần cho cổng intent |
| `ENABLE_GET_SUB_COMMENTS` | False | |
| `ENABLE_GET_MEIDAS` | False | Tải ảnh/video crawler (khác TREND_DOWNLOAD_MEDIA) |
| `ENABLE_GET_WORDCLOUD` | False | [wordcloud.md](../wordcloud.md) |
| `ENABLE_IP_PROXY` | False | [proxy.md](../proxy.md) |
| `IP_PROXY_PROVIDER_NAME` | `kuaidaili` | kuaidaili / wandouhttp / static |
| `CRAWLER_MAX_SLEEP_SEC` | 2 | |
| `XHS_INTERNATIONAL` | False | rednote.com |
| `DISABLE_SSL_VERIFY` | False | Chỉ proxy MITM lab |

File từng nền tảng: `config/{xhs,dy,ks,bilibili,weibo,tieba,zhihu,tiktok}_config.py` — danh sách ID, sort, field đặc thù.

### 8.2 Database — `config/db_config.py`

MySQL / Redis / MongoDB / SQLite crawler (`database/sqlite_tables.db`). Secret nên lấy từ env (`MYSQL_DB_PWD`, `REDIS_DB_PWD`, …). Không commit `.env` (đã gitignore).

### 8.3 Trend — `config/trend_config.py`

Thứ tự ghi đè: default module → `data/trend_settings.json` → env.

| Biến | Default | Tác động |
|------|---------|----------|
| `TREND_SCAN_INTERVAL_HOURS` | 6 | Chu kỳ scheduler nếu không có cron |
| `TREND_SCAN_CRON` | trống | Cron phút+giờ nếu set |
| `TREND_SNAPSHOT_GAP_HOURS` | 6 | Cách 2 snapshot |
| `TREND_ALERT_COOLDOWN_HOURS` | 12 | Không spam cùng SP |
| `TREND_VIDEOS_PER_ALERT` | 5 | |
| `TREND_VIDEO_MIN_AGE_HOURS` | 2 | Lọc clip quá mới |
| `TREND_VIDEO_MAX_AGE_DAYS` | 10 | Lọc clip quá cũ |
| `TREND_MIN_CONFIDENCE` | 4 | Ngưỡng Telegram |
| `TREND_MIN_MENTION` / `TREND_MIN_SPREAD` | 5 / 3 | Cổng mention_spread |
| `TREND_MIN_INTENT_N` / `TREND_MIN_INTENT_WILSON` | 8 / 0.08 | Cổng intent |
| `TREND_HOT_HEATNOW` | 0.70 | Label DANG HOT |
| `TREND_RISING_HEATNOW_MIN` / `TREND_RISING_DELTA_RATIO` | 0.40 / 0.25 | DU KIEN NONG |
| `TREND_GOOGLE_TRENDS_ENABLED` | true | Cổng CN |
| `TREND_LLM_ENABLED` | false | Chỉ gợi ý tên, không thay cổng |
| `TREND_DOWNLOAD_MEDIA` | false | mp4 khi scan |
| `TREND_MARKETPLACE_ENABLED` | true | Draft Shopee/Lazada |
| `TREND_SCHEDULER_ENABLED` | false | Vòng nền |
| `TREND_PLATFORMS` | `dy,tiktok` | |
| `TREND_WEIGHT_*` | 0.35/0.20/0.20/0.15/0.10 | HeatNow |
| `TREND_TELEGRAM_BOT_TOKEN` / `CHAT_ID` | trống | Outbound |
| `TREND_DB_PATH` | `data/trend.sqlite` | |
| `TREND_SETTINGS_PATH` | `data/trend_settings.json` | |

### 8.4 Lưu crawler

| `SAVE_DATA_OPTION` | Khi dùng |
|--------------------|----------|
| `jsonl` (mặc định) | Append, crawl tăng dần |
| `json` / `csv` | Xem nhanh, explorer UI |
| `excel` | Báo cáo; flush lúc shutdown |
| `sqlite` | Local, `--init_db sqlite` |
| `db` | MySQL production |
| `postgres` | PostgreSQL |
| `mongodb` | Schema lỏng |

Hướng dẫn: [data_storage_guide.md](../data_storage_guide.md), [excel_export_guide.md](../excel_export_guide.md).

---

## 9. Dữ liệu trên đĩa

| Path | Nội dung | Git |
|------|----------|-----|
| `data/{platform}/` | JSONL/CSV/Excel crawl | gitignore `/data/` |
| `data/trend.sqlite` | Read model radar | gitignore |
| `data/trend_settings.json` | Settings WebUI | gitignore theo `/data/` |
| `database/sqlite_tables.db` | ORM crawler | `database/*.db` gitignore |
| `database/agent_memory.db` | Hội thoại Agent | gitignore |
| `{platform}_user_data_dir` | Profile Chrome/Playwright | `browser_data/` gitignore |

Backup `data/trend.sqlite` nếu cần giữ bảng xếp hạng. Cookie/login nằm user data dir — không commit.

---

## 10. Khi gặp sự cố

| Triệu chứng | Việc làm |
|-------------|----------|
| Env check fail | `uv sync`; chạy `uv run main.py --help` trong thư mục gốc |
| WebUI trống / JSON “not found” | `cd webui && npm run build` hoặc dùng Vite `:5173` |
| Vite không có log crawler | API `:8080` phải chạy; proxy `/api` |
| QR không hiện / login fail | `HEADLESS=False`; CDP Allow remote debugging; [cdp-mode.md](../cdp-mode.md) |
| Xiaohongshu kẹt slider | Mở cửa sổ, qua captcha tay; cookie dễ hỏng |
| Douyin hỏi SĐT sau QR | Qua tay trên cửa sổ Chrome |
| “Crawler is already running” | Stop trên UI hoặc đợi process thoát |
| Lần 1 không Telegram | Đúng: cần 2 snapshot + Confidence ≥ 4 |
| Alert không tới | Token/chat id; `POST /api/trend/telegram/test`; cooldown 12h |
| Agent “đang xử lý tin trước” | Lock hội thoại; đợi hoặc tăng `AGENT_MEMORY_LOCK_TTL` |
| Agent không crawl khi hỏi “mới nhất” | Đúng: chỉ `search_crawl_results`. Nói rõ “crawl …” + đủ quyền |
| JSONL không thấy trên Data explorer | Explorer chỉ json/csv/xlsx — mở file trong `data/{platform}/` |
| Proxy | [proxy.md](../proxy.md), [kuaidaili-proxy.md](../kuaidaili-proxy.md), [wandou-http-proxy.md](../wandou-http-proxy.md) |

FAQ cũ: [faq.md](../faq.md).

---

## 11. Kiểm tra nhanh sau cài

```bash
uv run pytest tests/test_app_wiring.py tests/test_product_identity.py tests/test_agent_policy.py
uv run main.py --help
uv run uvicorn api.main:app --port 8080
```

Mở `/docs` và `/api/health`. Chưa cần crawl thật để xác nhận process sống.
