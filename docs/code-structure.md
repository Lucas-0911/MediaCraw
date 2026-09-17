# Source layout

Trend Radar is an agent-orchestrated product. The crawler engine (`media_platform/`, `main.py`) is a subsystem, not the façade.

Chi tiết từng package: [handbook/architecture.md](handbook/architecture.md). Vận hành: [handbook/usage.md](handbook/usage.md).

```
├── app/                    # Composition root (wiring, CLI alias)
├── agent/                  # Agent loop, memory, tools
│   ├── core/
│   ├── memory/
│   └── tools/
├── channels/telegram/      # Inbound Telegram adapter (no SQL)
├── services/               # HTTP-free application services
├── api/                    # FastAPI routers, schemas, app factory
├── config/                 # base_config + per-platform + trend + agent
├── media_platform/         # Crawler engine: xhs, dy, ks, bili, wb, tieba, zhihu, tiktok
├── store/                  # File/DB writers; Douyin/TikTok hook Trend Radar
├── trend/                  # Extract, score, alerts, scheduler, marketplace
├── database/               # ORM including agent conversation tables
├── webui/                  # React: SCAN + TREND_RADAR
├── tests/
├── libs/                   # Platform JS helpers
├── proxy/                  # IP pool
├── tools/                  # CDP, Playwright, utilities
├── main.py                 # Crawler CLI (`uv run python main.py`)
├── recv_sms.py             # OTP webhook for phone login
└── var.py
```

Dependency rule:

```
channels → agent → tools → services → crawler engine
api routers → services
TelegramAdapter ↛ SQL, ↛ media_platform
AgentLoop ↛ SQL (uses AgentMemory)
```

Upstream crawler origin is recorded in [NOTICE](../NOTICE).
