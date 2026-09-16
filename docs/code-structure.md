# Cấu trúc mã nguồn

```
├── api/                    # FastAPI: crawler, data, websocket, trend
├── config/                 # base_config + từng nền tảng + trend_config
├── media_platform/         # xhs, dy, ks, bili, wb, tieba, zhihu, tiktok
├── store/                  # ghi file/DB; douyin/tiktok hook Trend Radar
├── trend/                  # extract, score, Telegram, scheduler, marketplace
├── database/               # ORM
├── webui/                  # React: SCAN + TREND_RADAR
├── tests/                  # pytest
├── libs/                   # douyin.js, zhihu.js, stealth.min.js
├── proxy/                  # pool IP
├── tools/                  # CDP, Playwright, tiện ích
├── main.py                 # CLI
├── recv_sms.py             # webhook OTP (phone login)
└── var.py
```
