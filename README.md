# Trend Radar

Sản phẩm tìm **sản phẩm đang / sắp hot ở Trung Quốc** (Douyin), lấy video xu hướng gắn sản phẩm, rồi gửi **Telegram** khi đủ Confidence. TikTok VN là nguồn nhiệt phụ. Crawler đa nền tảng (fork MediaCrawler) vẫn dùng để thu thập.

[Tiếng Việt](README.md) · [English](README_en.md) · [Español](README_es.md)

Người vận hành tự chịu trách nhiệm về điều khoản nền tảng, dữ liệu và cách dùng sản phẩm. License thương mại: [LICENSE](LICENSE). Nguồn gốc MediaCrawler: [NOTICE](NOTICE).

## Làm gì

1. Crawl Douyin (và tùy chọn TikTok VN) theo keyword ngành.
2. Nhận diện SKU (小黄车 / `product_id`) hoặc tên lặp trên nhiều video.
3. Chấm **HeatNow** + **Confidence 0–5** trên **hai snapshot** (khoảng cách do bạn cấu hình).
4. Telegram khi `Confidence >= TREND_MIN_CONFIDENCE` (mặc định 4): tên SP, breakdown công thức, N video.
5. Tùy chọn: LLM gợi ý tên, tải mp4, draft listing Shopee/Lazada (không checkout ẩn, không scrape FastMoss / 蝉妈妈 / 飞瓜).

```
HeatNow = 0.35 play_velocity
        + 0.20 eng_velocity
        + 0.20 mention
        + 0.15 spread
        + 0.10 intent_wilson
```

Google Trends `geo=CN` là cổng xác nhận riêng, không cộng vào HeatNow. Trọng số và mọi ngưỡng nằm ở `config/trend_config.py`, env, hoặc form **Trend settings** trên WebUI (`data/trend_settings.json`).

## Nền tảng crawl

| Nền tảng | Search | Detail | Comment | Trend Radar ingest |
| -------- | ------ | ------ | ------- | ------------------ |
| Douyin (`dy`) | có | có | có | nguồn nhiệt chính |
| TikTok VN (`tiktok`) | có | có | có | nguồn phụ |
| Xiaohongshu, Kuaishou, Bilibili, Weibo, Tieba, Zhihu | có | có | có | không chấm heat SP TQ |

## Cài đặt

- Python 3.11 + [uv](https://docs.astral.sh/uv/getting-started/installation)
- Node.js >= 16
- Chrome >= 144 nếu dùng CDP (mặc định)

```bash
uv sync
uv run playwright install   # chỉ khi không dùng CDP
cd webui && npm install
```

CDP: Chrome `chrome://inspect/#remote-debugging` → Allow remote debugging → `127.0.0.1:9222`. Tắt CDP: `ENABLE_CDP_MODE = False` trong `config/base_config.py`.

## Chạy

### WebUI (khuyến nghị)

```bash
# Terminal 1
uv run uvicorn api.main:app --port 8080 --reload

# Terminal 2
cd webui && npm run dev
```

Mở http://localhost:5173/

- Tab **SCAN**: crawl (keyword, QR/cookie, comment).
- Tab **TREND_RADAR**: bảng xếp hạng SP, form chu kỳ quét / số video / Telegram, nút RUN_SCORE, scheduler, draft Shopee/Lazada, tải mp4.

Lớp Agent (`agent/`, `channels/telegram/`) là lối vào hội thoại: tin nhắn thường đi qua AgentLoop + memory; lệnh slash (`/status`, `/crawl`, …) vẫn do handler cũ. Crawler subprocess giữ nguyên `uv run python main.py`.

Hướng dẫn UI chi tiết: [docs/webui-guide.md](docs/webui-guide.md).

Build một process:

```bash
cd webui && npm run build
uv run uvicorn api.main:app --port 8080
```

Mở http://localhost:8080/

### CLI crawl

```bash
uv run main.py --platform dy --lt qrcode --type search --keywords "美白精华"
uv run main.py --platform tiktok --lt qrcode --type search --keywords "skincare"
uv run main.py --help
```

Bật comment (`ENABLE_GET_COMMENTS`) nếu dùng cổng intent mua. Dữ liệu crawl: `data/{platform}/`. Dữ liệu radar: `data/trend.sqlite`.

## Trend Radar — luồng dùng

1. Điền Trend settings (hoặc để default). Token Telegram: `TREND_TELEGRAM_BOT_TOKEN` + `TREND_TELEGRAM_CHAT_ID`.
2. Crawl Douyin keyword tiếng Trung; lần 1 chỉ snapshot (nhãn QUAN SAT).
3. Sau `TREND_SNAPSHOT_GAP_HOURS` (mặc định 6h) crawl/score lại.
4. RUN_SCORE hoặc bật scheduler. Telegram chỉ khi đủ Confidence **và** đã có 2 snapshot.

API: `GET /api/trend/products`, `PUT /api/trend/settings`, `POST /api/trend/scan`, Swagger http://localhost:8080/docs

### Cấu hình hay dùng

| Biến | Ý nghĩa | Default |
| ---- | -------- | ------- |
| `TREND_SCAN_INTERVAL_HOURS` / `TREND_SCAN_CRON` | Chu kỳ score | 6h / trống |
| `TREND_SNAPSHOT_GAP_HOURS` | Cách 2 snapshot | 6 |
| `TREND_VIDEOS_PER_ALERT` | Số video trong Telegram | 5 |
| `TREND_VIDEO_MIN_AGE_HOURS` / `TREND_VIDEO_MAX_AGE_DAYS` | Lọc tuổi clip | 2h / 10 ngày |
| `TREND_MIN_CONFIDENCE` | Ngưỡng gửi Telegram | 4 |
| `TREND_LLM_ENABLED` | Gợi ý tên SP (không thay cổng) | false |
| `TREND_DOWNLOAD_MEDIA` | Tải mp4 | false |
| `TREND_MARKETPLACE_ENABLED` | Draft Shopee/Lazada | true |
| `TREND_SCHEDULER_ENABLED` | Vòng lặp nền | false |

## Không làm

- Scrape 蝉妈妈 / 飞瓜 / FastMoss / Kalodata
- Thanh toán Shopee/Lazada tự động (OTP / 2FA / captcha)

## Tài liệu đầy đủ

- [docs/handbook/usage.md](docs/handbook/usage.md) — hướng dẫn vận hành từng lối vào
- [docs/handbook/architecture.md](docs/handbook/architecture.md) — kiến trúc từng package
- [docs/README.md](docs/README.md) — mục lục
- [docs/webui-guide.md](docs/webui-guide.md)
- [docs/data_storage_guide.md](docs/data_storage_guide.md)
- [docs/cdp-mode.md](docs/cdp-mode.md)

## Nguồn gốc

Phần crawler đa nền tảng xuất phát từ [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) (relakkes@gmail.com). Product này vận hành độc lập theo [LICENSE](LICENSE); ghi nhận upstream trong [NOTICE](NOTICE).
