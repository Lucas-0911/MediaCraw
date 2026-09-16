# Trend Radar

Encuentra **productos que están o van a estar calientes en China** (Douyin), adjunta videos de tendencia y envía **Telegram** cuando Confidence es suficientemente alto. TikTok Vietnam es una fuente de calor secundaria. El crawler multiplataforma (fork de MediaCrawler) sigue recolectando los datos.

[Tiếng Việt](README.md) · [English](README_en.md) · [Español](README_es.md)

El operador asume ToS de las plataformas, datos y el uso del producto. Licencia comercial: [LICENSE](LICENSE). Origen MediaCrawler: [NOTICE](NOTICE).

## Qué hace

1. Crawl de Douyin (TikTok VN opcional) por keywords de industria.
2. Identifica SKU (小黄车 / `product_id`) o nombres repetidos en varios videos.
3. Calcula **HeatNow** + **Confidence 0–5** con **dos snapshots** (intervalo configurable).
4. Telegram si `Confidence >= TREND_MIN_CONFIDENCE` (default 4): producto, fórmula, N videos.
5. Opcional: LLM para nombres, descarga mp4, borradores Shopee/Lazada (sin checkout oculto; sin scrape de FastMoss / 蝉妈妈 / 飞瓜).

```
HeatNow = 0.35 play_velocity
        + 0.20 eng_velocity
        + 0.20 mention
        + 0.15 spread
        + 0.10 intent_wilson
```

Google Trends `geo=CN` es un gate aparte, no entra en HeatNow. Pesos y umbrales: `config/trend_config.py`, env o el formulario **Trend settings** (`data/trend_settings.json`).

## Plataformas

| Plataforma | Search | Detail | Comentarios | Ingest Trend Radar |
| ---------- | ------ | ------ | ----------- | ------------------ |
| Douyin (`dy`) | sí | sí | sí | calor principal |
| TikTok VN (`tiktok`) | sí | sí | sí | secundario |
| Xiaohongshu, Kuaishou, Bilibili, Weibo, Tieba, Zhihu | sí | sí | sí | sin heat de producto CN |

## Instalación

- Python 3.11 + [uv](https://docs.astral.sh/uv/getting-started/installation)
- Node.js >= 16
- Chrome >= 144 si usas CDP (por defecto)

```bash
uv sync
uv run playwright install
cd webui && npm install
```

CDP: Chrome `chrome://inspect/#remote-debugging` → Allow remote debugging → `127.0.0.1:9222`.

## Ejecutar

```bash
uv run uvicorn api.main:app --port 8080 --reload
cd webui && npm run dev
```

Abre http://localhost:5173/ — pestaña **SCAN** (crawler) y **TREND_RADAR** (ranking, settings, Telegram).

Guía UI: [docs/webui-guide.md](docs/webui-guide.md). CLI: `uv run main.py --platform dy --lt qrcode --type search`.

Radar DB: `data/trend.sqlite`. Crawl: `data/{platform}/`.

Telegram: `TREND_TELEGRAM_BOT_TOKEN` + `TREND_TELEGRAM_CHAT_ID`. Primera pasada = snapshot; la segunda, tras `TREND_SNAPSHOT_GAP_HOURS`, puede alertar.

## Fuera de alcance

- Scrape de 蝉妈妈 / 飞瓜 / FastMoss / Kalodata
- Pago automático en Shopee/Lazada (OTP / 2FA / captcha)

## Origen

Crawler derivado de [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler). Licencia del producto: [LICENSE](LICENSE). Crédito upstream: [NOTICE](NOTICE).
