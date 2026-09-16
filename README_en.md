# Trend Radar

Find **products that are hot or about to heat up in China** (Douyin), attach trending videos, and send **Telegram** when Confidence is high enough. TikTok Vietnam is a secondary heat source. The multi-platform crawler (MediaCrawler fork) still collects the raw data.

[Tiếng Việt](README.md) · [English](README_en.md) · [Español](README_es.md)

The operator owns platform ToS, data, and product-use risk. Commercial license: [LICENSE](LICENSE). MediaCrawler origin: [NOTICE](NOTICE).

## What it does

1. Crawl Douyin (optional TikTok VN) by industry keywords.
2. Identify SKUs (小黄车 / `product_id`) or names that repeat across videos.
3. Score **HeatNow** + **Confidence 0–5** on **two snapshots** (gap is configurable).
4. Telegram when `Confidence >= TREND_MIN_CONFIDENCE` (default 4): product info, formula breakdown, N videos.
5. Optional: LLM name hints, mp4 download, Shopee/Lazada draft listings (no stealth checkout; no FastMoss / 蝉妈妈 / 飞瓜 scraping).

```
HeatNow = 0.35 play_velocity
        + 0.20 eng_velocity
        + 0.20 mention
        + 0.15 spread
        + 0.10 intent_wilson
```

Google Trends `geo=CN` is a separate confirmation gate, not mixed into HeatNow. Weights and thresholds live in `config/trend_config.py`, env, or the WebUI **Trend settings** form (`data/trend_settings.json`).

## Crawl platforms

| Platform | Search | Detail | Comments | Trend Radar ingest |
| -------- | ------ | ------ | -------- | ------------------ |
| Douyin (`dy`) | yes | yes | yes | primary heat |
| TikTok VN (`tiktok`) | yes | yes | yes | secondary |
| Xiaohongshu, Kuaishou, Bilibili, Weibo, Tieba, Zhihu | yes | yes | yes | no CN product heat |

## Setup

- Python 3.11 + [uv](https://docs.astral.sh/uv/getting-started/installation)
- Node.js >= 16
- Chrome >= 144 if using CDP (default)

```bash
uv sync
uv run playwright install   # only if not using CDP
cd webui && npm install
```

CDP: Chrome `chrome://inspect/#remote-debugging` → Allow remote debugging → `127.0.0.1:9222`. Disable CDP: `ENABLE_CDP_MODE = False` in `config/base_config.py`.

## Run

### WebUI (recommended)

```bash
# Terminal 1
uv run uvicorn api.main:app --port 8080 --reload

# Terminal 2
cd webui && npm run dev
```

Open http://localhost:5173/

- **SCAN**: classic crawler (keywords, QR/cookie, comments).
- **TREND_RADAR**: product ranking, scan/video/Telegram settings, RUN_SCORE, scheduler, marketplace drafts, mp4 download.

UI guide: [docs/webui-guide.md](docs/webui-guide.md).

Single-process build:

```bash
cd webui && npm run build
uv run uvicorn api.main:app --port 8080
```

Open http://localhost:8080/

### CLI crawl

```bash
uv run main.py --platform dy --lt qrcode --type search --keywords "美白精华"
uv run main.py --platform tiktok --lt qrcode --type search --keywords "skincare"
uv run main.py --help
```

Enable comments (`ENABLE_GET_COMMENTS`) for the purchase-intent gate. Crawl files: `data/{platform}/`. Radar DB: `data/trend.sqlite`.

## Trend Radar usage

1. Fill Trend settings (or keep defaults). Telegram: `TREND_TELEGRAM_BOT_TOKEN` + `TREND_TELEGRAM_CHAT_ID`.
2. Crawl Douyin with Chinese industry keywords; first pass is snapshot only (label QUAN SAT).
3. After `TREND_SNAPSHOT_GAP_HOURS` (default 6h) crawl/score again.
4. RUN_SCORE or enable the scheduler. Telegram only with enough Confidence **and** two snapshots.

API: `GET /api/trend/products`, `PUT /api/trend/settings`, `POST /api/trend/scan`, Swagger http://localhost:8080/docs

### Common settings

| Variable | Meaning | Default |
| -------- | ------- | ------- |
| `TREND_SCAN_INTERVAL_HOURS` / `TREND_SCAN_CRON` | Score interval | 6h / empty |
| `TREND_SNAPSHOT_GAP_HOURS` | Gap between snapshots | 6 |
| `TREND_VIDEOS_PER_ALERT` | Videos in Telegram | 5 |
| `TREND_VIDEO_MIN_AGE_HOURS` / `TREND_VIDEO_MAX_AGE_DAYS` | Clip age filter | 2h / 10 days |
| `TREND_MIN_CONFIDENCE` | Telegram threshold | 4 |
| `TREND_LLM_ENABLED` | Name hint (does not replace gates) | false |
| `TREND_DOWNLOAD_MEDIA` | Download mp4 | false |
| `TREND_MARKETPLACE_ENABLED` | Shopee/Lazada drafts | true |
| `TREND_SCHEDULER_ENABLED` | Background loop | false |

## Out of scope

- Scraping 蝉妈妈 / 飞瓜 / FastMoss / Kalodata
- Automatic Shopee/Lazada payment (OTP / 2FA / captcha)

## More docs

- [docs/README.md](docs/README.md) — docs index
- [docs/webui-guide.md](docs/webui-guide.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/data_storage_guide.md](docs/data_storage_guide.md)
- [docs/cdp-mode.md](docs/cdp-mode.md)

## Origin

The multi-platform crawler started from [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) (relakkes@gmail.com). This product runs under [LICENSE](LICENSE); upstream credit is in [NOTICE](NOTICE).
