# Tài liệu kiến trúc Trend Radar / crawler

## 1. Tổng quan dự án

### 1.1 Giới thiệu

Product **Trend Radar**: crawl Douyin (TikTok VN phụ) để tìm sản phẩm hot Trung Quốc, chấm HeatNow/Confidence, gửi Telegram. Lớp crawler đa nền tảng xuất phát từ MediaCrawler.

### 1.2 Nền tảng hỗ trợ

| Nền tảng | Mã | Chức năng chính |
|------|------|---------|
| Douyin | `dy` | Tìm video, chi tiết, creator — nguồn nhiệt chính |
| TikTok VN | `tiktok` | Tìm video, chi tiết — nguồn nhiệt phụ |
| Xiaohongshu | `xhs` | Tìm ghi chú, chi tiết, creator |
| Kuaishou | `ks` | Tìm video, chi tiết, creator |
| Bilibili | `bili` | Tìm video, chi tiết, UP |
| Weibo | `wb` | Tìm weibo, chi tiết, blogger |
| Baidu Tieba | `tieba` | Tìm bài, chi tiết |
| Zhihu | `zhihu` | Tìm Q&A, chi tiết, người trả lời |

### 1.3 Tính năng cốt lõi

- **Nhiều nền tảng**: giao diện crawler thống nhất, Douyin/TikTok cho Trend Radar
- **Trend Radar**: HeatNow, Confidence, Telegram, draft Shopee/Lazada
- **Nhiều cách đăng nhập**: QR, số điện thoại, Cookie
- **Nhiều cách lưu**: CSV, JSON, JSONL, SQLite, MySQL, MongoDB, Excel
- **Chống phát hiện**: chế độ CDP, pool IP proxy, ký request
- **Bất đồng bộ**: asyncio

---

## 2. Kiến trúc tổng thể

### 2.1 Sơ đồ tầng cao

```mermaid
flowchart TB
    subgraph Entry["Tầng lối vào"]
        main["main.py<br/>Entry chương trình"]
        cmdarg["cmd_arg<br/>Tham số CLI"]
        config["config<br/>Quản lý cấu hình"]
    end

    subgraph Core["Tầng crawler lõi"]
        factory["CrawlerFactory<br/>Factory crawler"]
        base["AbstractCrawler<br/>Lớp cơ sở crawler"]

        subgraph Platforms["Implement nền tảng"]
            xhs["XiaoHongShuCrawler"]
            dy["DouYinCrawler"]
            ks["KuaishouCrawler"]
            bili["BilibiliCrawler"]
            wb["WeiboCrawler"]
            tieba["TieBaCrawler"]
            zhihu["ZhihuCrawler"]
        end
    end

    subgraph Client["Tầng API client"]
        absClient["AbstractApiClient<br/>Lớp cơ sở client"]
        xhsClient["XiaoHongShuClient"]
        dyClient["DouYinClient"]
        ksClient["KuaiShouClient"]
        biliClient["BilibiliClient"]
        wbClient["WeiboClient"]
        tiebaClient["BaiduTieBaClient"]
        zhihuClient["ZhiHuClient"]
    end

    subgraph Storage["Tầng lưu trữ"]
        storeFactory["StoreFactory<br/>Factory lưu trữ"]
        csv["CSV"]
        json["JSON"]
        sqlite["SQLite"]
        mysql["MySQL"]
        mongodb["MongoDB"]
        excel["Excel"]
    end

    subgraph Infra["Tầng hạ tầng"]
        browser["Quản lý trình duyệt<br/>Playwright/CDP"]
        proxy["Pool IP proxy"]
        cache["Hệ thống cache"]
        login["Quản lý đăng nhập"]
    end

    main --> factory
    cmdarg --> main
    config --> main
    factory --> base
    base --> Platforms
    Platforms --> Client
    Client --> Storage
    Client --> Infra
    Storage --> storeFactory
    storeFactory --> csv & json & sqlite & mysql & mongodb & excel
```

### 2.2 Luồng dữ liệu

```mermaid
flowchart LR
    subgraph Input["Đầu vào"]
        keywords["Từ khóa / ID"]
        config["Tham số cấu hình"]
    end

    subgraph Process["Xử lý"]
        browser["Mở trình duyệt"]
        login["Đăng nhập"]
        search["Tìm / crawl"]
        parse["Parse dữ liệu"]
        comment["Lấy comment"]
    end

    subgraph Output["Đầu ra"]
        content["Nội dung"]
        comments["Comment"]
        creator["Creator"]
        media["File media"]
    end

    subgraph Storage["Lưu trữ"]
        file["File<br/>CSV/JSON/Excel"]
        db["Database<br/>SQLite/MySQL"]
        nosql["NoSQL<br/>MongoDB"]
    end

    keywords --> browser
    config --> browser
    browser --> login
    login --> search
    search --> parse
    parse --> comment
    parse --> content
    comment --> comments
    parse --> creator
    parse --> media
    content & comments & creator --> file & db & nosql
    media --> file
```

---

## 3. Cấu trúc thư mục

```
MediaCrawler/
├── main.py                 # Entry chương trình
├── var.py                  # Biến context toàn cục
├── pyproject.toml          # Cấu hình dự án
│
├── base/                   # Lớp trừu tượng
│   └── base_crawler.py     # Cơ sở crawler, login, store, client
│
├── config/                 # Quản lý cấu hình
│   ├── base_config.py      # Cấu hình lõi
│   ├── db_config.py        # Cấu hình database
│   └── {platform}_config.py # Cấu hình từng nền tảng
│
├── media_platform/         # Implement crawler nền tảng
│   ├── xhs/                # Xiaohongshu
│   ├── douyin/             # Douyin
│   ├── kuaishou/           # Kuaishou
│   ├── bilibili/           # Bilibili
│   ├── weibo/              # Weibo
│   ├── tieba/              # Baidu Tieba
│   └── zhihu/              # Zhihu
│
├── store/                  # Lưu trữ dữ liệu
│   ├── excel_store_base.py # Cơ sở lưu Excel
│   └── {platform}/         # Implement từng nền tảng
│
├── database/               # Tầng database
│   ├── models.py           # Model ORM
│   ├── db_session.py       # Session
│   └── mongodb_store_base.py # Cơ sở MongoDB
│
├── proxy/                  # Quản lý proxy
│   ├── proxy_ip_pool.py    # Pool IP
│   ├── proxy_mixin.py      # Mixin làm mới proxy
│   └── providers/          # Nhà cung cấp proxy
│
├── cache/                  # Cache
│   ├── abs_cache.py        # Lớp trừu tượng
│   ├── local_cache.py      # Cache local
│   └── redis_cache.py      # Cache Redis
│
├── tools/                  # Tiện ích
│   ├── app_runner.py       # Chạy ứng dụng, shutdown
│   ├── browser_launcher.py # Mở trình duyệt
│   ├── cdp_browser.py      # Quản lý CDP
│   ├── crawler_util.py     # Tiện ích crawler
│   └── async_file_writer.py # Ghi file bất đồng bộ
│
├── model/                  # Model dữ liệu
│   └── m_{platform}.py     # Model Pydantic
│
├── libs/                   # Thư viện JS
│   └── stealth.min.js      # Script chống phát hiện
│
└── cmd_arg/                # Tham số CLI
    └── arg.py              # Định nghĩa tham số
```

---

## 4. Module lõi

### 4.1 Hệ lớp cơ sở crawler

```mermaid
classDiagram
    class AbstractCrawler {
        <<abstract>>
        +start()* Khởi động crawler
        +search()* Tìm kiếm
        +launch_browser() Mở trình duyệt
        +launch_browser_with_cdp() Mở bằng CDP
    }

    class AbstractLogin {
        <<abstract>>
        +begin()* Bắt đầu đăng nhập
        +login_by_qrcode()* Đăng nhập QR
        +login_by_mobile()* Đăng nhập SĐT
        +login_by_cookies()* Đăng nhập Cookie
    }

    class AbstractStore {
        <<abstract>>
        +store_content()* Lưu nội dung
        +store_comment()* Lưu comment
        +store_creator()* Lưu creator
        +store_image()* Lưu ảnh
        +store_video()* Lưu video
    }

    class AbstractApiClient {
        <<abstract>>
        +request()* HTTP request
        +update_cookies()* Cập nhật Cookie
    }

    class ProxyRefreshMixin {
        +init_proxy_pool() Khởi tạo pool proxy
        +_refresh_proxy_if_expired() Làm mới proxy hết hạn
    }

    class XiaoHongShuCrawler {
        +xhs_client: XiaoHongShuClient
        +start()
        +search()
        +get_specified_notes()
        +get_creators_and_notes()
    }

    class XiaoHongShuClient {
        +playwright_page: Page
        +cookie_dict: Dict
        +request()
        +pong() Kiểm tra trạng thái đăng nhập
        +get_note_by_keyword()
        +get_note_by_id()
    }

    AbstractCrawler <|-- XiaoHongShuCrawler
    AbstractApiClient <|-- XiaoHongShuClient
    ProxyRefreshMixin <|-- XiaoHongShuClient
```

### 4.2 Vòng đời crawler

```mermaid
sequenceDiagram
    participant Main as main.py
    participant Factory as CrawlerFactory
    participant Crawler as XiaoHongShuCrawler
    participant Browser as Playwright/CDP
    participant Login as XiaoHongShuLogin
    participant Client as XiaoHongShuClient
    participant Store as StoreFactory

    Main->>Factory: create_crawler("xhs")
    Factory-->>Main: instance crawler

    Main->>Crawler: start()

    alt Bật IP proxy
        Crawler->>Crawler: create_ip_pool()
    end

    alt Chế độ CDP
        Crawler->>Browser: launch_browser_with_cdp()
    else Chế độ chuẩn
        Crawler->>Browser: launch_browser()
    end
    Browser-->>Crawler: browser_context

    Crawler->>Crawler: create_xhs_client()
    Crawler->>Client: pong() kiểm tra đăng nhập

    alt Chưa đăng nhập
        Crawler->>Login: begin()
        Login->>Login: login_by_qrcode/mobile/cookie
        Login-->>Crawler: đăng nhập thành công
    end

    alt mode search
        Crawler->>Client: get_note_by_keyword()
        Client-->>Crawler: kết quả tìm
        loop Lấy chi tiết
            Crawler->>Client: get_note_by_id()
            Client-->>Crawler: chi tiết ghi chú
        end
    else mode detail
        Crawler->>Client: get_note_by_id()
    else mode creator
        Crawler->>Client: get_creator_info()
    end

    Crawler->>Store: store_content/comment/creator
    Store-->>Crawler: lưu xong

    Main->>Crawler: cleanup()
    Crawler->>Browser: close()
```

### 4.3 Cấu trúc implement từng nền tảng

Mỗi thư mục nền tảng gồm:

```
media_platform/{platform}/
├── __init__.py         # Export module
├── core.py             # Class crawler chính
├── client.py           # API client
├── login.py            # Đăng nhập
├── field.py            # Field / enum
├── exception.py        # Exception
├── help.py             # Hàm phụ
└── {implement đặc thù}.py
```

### 4.4 Ba mode crawler

| Mode | Giá trị config | Mô tả | Khi dùng |
|------|--------|---------|---------|
| Search | `search` | Tìm nội dung theo từ khóa | Lấy hàng loạt theo chủ đề |
| Detail | `detail` | Lấy chi tiết theo ID | Đã biết ID |
| Creator | `creator` | Lấy toàn bộ nội dung creator | Theo dõi blogger / UP |

---

## 5. Tầng lưu trữ

### 5.1 Sơ đồ lưu trữ

```mermaid
classDiagram
    class AbstractStore {
        <<abstract>>
        +store_content()*
        +store_comment()*
        +store_creator()*
    }

    class StoreFactory {
        +STORES: Dict
        +create_store() AbstractStore
    }

    class CsvStoreImplement {
        +async_file_writer: AsyncFileWriter
        +store_content()
        +store_comment()
    }

    class JsonStoreImplement {
        +async_file_writer: AsyncFileWriter
        +store_content()
        +store_comment()
    }

    class DbStoreImplement {
        +session: AsyncSession
        +store_content()
        +store_comment()
    }

    class SqliteStoreImplement {
        +session: AsyncSession
        +store_content()
        +store_comment()
    }

    class MongoStoreImplement {
        +mongo_base: MongoDBStoreBase
        +store_content()
        +store_comment()
    }

    class ExcelStoreImplement {
        +excel_base: ExcelStoreBase
        +store_content()
        +store_comment()
    }

    AbstractStore <|-- CsvStoreImplement
    AbstractStore <|-- JsonStoreImplement
    AbstractStore <|-- DbStoreImplement
    AbstractStore <|-- SqliteStoreImplement
    AbstractStore <|-- MongoStoreImplement
    AbstractStore <|-- ExcelStoreImplement
    StoreFactory --> AbstractStore
```

### 5.2 Factory lưu trữ

```python
# Ví dụ Douyin
class DouyinStoreFactory:
    STORES = {
        "csv": DouyinCsvStoreImplement,
        "db": DouyinDbStoreImplement,
        "json": DouyinJsonStoreImplement,
        "sqlite": DouyinSqliteStoreImplement,
        "mongodb": DouyinMongoStoreImplement,
        "excel": DouyinExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = DouyinStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        return store_class()
```

### 5.3 So sánh cách lưu

| Cách lưu | Giá trị config | Ưu điểm | Khi dùng |
|---------|--------|-----|---------|
| CSV | `csv` | Đơn giản, phổ biến | Dữ liệu nhỏ, xem nhanh |
| JSON | `json` | Cấu trúc đầy đủ, dễ parse | API, trao đổi dữ liệu |
| JSONL | `jsonl` | Append, hiệu năng tốt | Dữ liệu lớn, crawl tăng dần (mặc định) |
| SQLite | `sqlite` | Nhẹ, không cần server | Local, dự án nhỏ |
| MySQL | `db` | Hiệu năng, đồng thời | Production, dữ liệu lớn |
| MongoDB | `mongodb` | Linh hoạt, dễ mở rộng | Dữ liệu phi cấu trúc |
| Excel | `excel` | Trực quan, dễ chia sẻ | Báo cáo, phân tích |

---

## 6. Tầng hạ tầng

### 6.1 Kiến trúc proxy

```mermaid
flowchart TB
    subgraph Config["Cấu hình"]
        enable["ENABLE_IP_PROXY"]
        provider["IP_PROXY_PROVIDER"]
        count["IP_PROXY_POOL_COUNT"]
    end

    subgraph Pool["Quản lý pool proxy"]
        pool["ProxyIpPool"]
        load["load_proxies()"]
        validate["_is_valid_proxy()"]
        get["get_proxy()"]
        refresh["get_or_refresh_proxy()"]
    end

    subgraph Providers["Nhà cung cấp"]
        kuaidl["Kuaidaili<br/>KuaiDaiLiProxy"]
        wandou["Wandou<br/>WanDouHttpProxy"]
        jishu["JiShu IP<br/>JiShuHttpProxy"]
    end

    subgraph Client["API client"]
        mixin["ProxyRefreshMixin"]
        request["request()"]
    end

    enable --> pool
    provider --> Providers
    count --> load
    pool --> load
    load --> validate
    validate --> Providers
    pool --> get
    pool --> refresh
    mixin --> refresh
    mixin --> Client
    request --> mixin
```

### 6.2 Luồng đăng nhập

```mermaid
flowchart TB
    Start([Bắt đầu đăng nhập]) --> CheckType{Kiểu đăng nhập?}

    CheckType -->|qrcode| QR[Hiện QR]
    QR --> WaitScan[Chờ quét]
    WaitScan --> CheckQR{Quét thành công?}
    CheckQR -->|Có| SaveCookie[Lưu Cookie]
    CheckQR -->|Không| WaitScan

    CheckType -->|phone| Phone[Nhập SĐT]
    Phone --> SendCode[Gửi OTP]
    SendCode --> Slider{Cần slider?}
    Slider -->|Có| DoSlider[Kéo slider]
    DoSlider --> InputCode[Nhập OTP]
    Slider -->|Không| InputCode
    InputCode --> Verify[Xác minh đăng nhập]
    Verify --> SaveCookie

    CheckType -->|cookie| LoadCookie[Nạp Cookie đã lưu]
    LoadCookie --> VerifyCookie{Cookie còn hạn?}
    VerifyCookie -->|Có| SaveCookie
    VerifyCookie -->|Không| Fail[Đăng nhập thất bại]

    SaveCookie --> UpdateContext[Cập nhật browser context]
    UpdateContext --> End([Đăng nhập xong])
```

### 6.3 Quản lý trình duyệt

```mermaid
flowchart LR
    subgraph Mode["Chế độ mở"]
        standard["Chuẩn<br/>Playwright"]
        cdp["CDP<br/>Chrome DevTools"]
    end

    subgraph Standard["Luồng chuẩn"]
        launch["chromium.launch()"]
        context["new_context()"]
        stealth["Inject stealth.js"]
    end

    subgraph CDP["Luồng CDP"]
        detect["Phát hiện đường dẫn trình duyệt"]
        start["Khởi động process"]
        connect["connect_over_cdp()"]
        cdpContext["Lấy context sẵn có"]
    end

    subgraph Features["Đặc tính"]
        f1["User data bền"]
        f2["Kế thừa extension và cài đặt"]
        f3["Chống phát hiện mạnh hơn"]
    end

    standard --> Standard
    cdp --> CDP
    CDP --> Features
```

### 6.4 Hệ thống cache

```mermaid
classDiagram
    class AbstractCache {
        <<abstract>>
        +get(key)* Lấy cache
        +set(key, value, expire)* Ghi cache
        +keys(pattern)* Lấy mọi key
    }

    class ExpiringLocalCache {
        -_cache: Dict
        -_expire_times: Dict
        +get(key)
        +set(key, value, expire_time)
        +keys(pattern)
        -_is_expired(key)
    }

    class RedisCache {
        -_client: Redis
        +get(key)
        +set(key, value, expire_time)
        +keys(pattern)
    }

    class CacheFactory {
        +create_cache(type) AbstractCache
    }

    AbstractCache <|-- ExpiringLocalCache
    AbstractCache <|-- RedisCache
    CacheFactory --> AbstractCache
```

---

## 7. Model dữ liệu

### 7.1 Quan hệ ORM

```mermaid
erDiagram
    DouyinAweme {
        int id PK
        string aweme_id UK
        string aweme_type
        string title
        string desc
        int create_time
        int liked_count
        int collected_count
        int comment_count
        int share_count
        string user_id FK
        datetime add_ts
        datetime last_modify_ts
    }

    DouyinAwemeComment {
        int id PK
        string comment_id UK
        string aweme_id FK
        string content
        int create_time
        int sub_comment_count
        string user_id
        datetime add_ts
        datetime last_modify_ts
    }

    DyCreator {
        int id PK
        string user_id UK
        string nickname
        string avatar
        string desc
        int follower_count
        int total_favorited
        datetime add_ts
        datetime last_modify_ts
    }

    DouyinAweme ||--o{ DouyinAwemeComment : "có"
    DyCreator ||--o{ DouyinAweme : "tạo"
```

### 7.2 Bảng theo nền tảng

| Nền tảng | Bảng nội dung | Bảng comment | Bảng creator |
|------|--------|--------|---------|
| Douyin | DouyinAweme | DouyinAwemeComment | DyCreator |
| Xiaohongshu | XHSNote | XHSNoteComment | XHSCreator |
| Kuaishou | KuaishouVideo | KuaishouVideoComment | KsCreator |
| Bilibili | BilibiliVideo | BilibiliVideoComment | BilibiliUpInfo |
| Weibo | WeiboNote | WeiboNoteComment | WeiboCreator |
| Tieba | TiebaNote | TiebaNoteComment | - |
| Zhihu | ZhihuContent | ZhihuContentComment | ZhihuCreator |

> Lưu ý: các bảng hồ sơ creator đã gỡ; user ID được hash thành `creator_hash`. Trend Radar lưu thêm `data/trend.sqlite`.

---

## 8. Hệ thống cấu hình

### 8.1 Mục cấu hình lõi

```python
# config/base_config.py

# Chọn nền tảng
PLATFORM = "xhs"  # xhs, dy, ks, bili, wb, tieba, zhihu

# Đăng nhập
LOGIN_TYPE = "qrcode"  # qrcode, phone, cookie
SAVE_LOGIN_STATE = True

# Crawler
CRAWLER_TYPE = "search"  # search, detail, creator
KEYWORDS = "编程副业,编程兼职"
CRAWLER_MAX_NOTES_COUNT = 15
MAX_CONCURRENCY_NUM = 1

# Comment
ENABLE_GET_COMMENTS = True
ENABLE_GET_SUB_COMMENTS = False
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# Trình duyệt
HEADLESS = False
ENABLE_CDP_MODE = True
CDP_DEBUG_PORT = 9222

# Proxy
ENABLE_IP_PROXY = False
IP_PROXY_PROVIDER = "kuaidaili"
IP_PROXY_POOL_COUNT = 2

# Lưu trữ
SAVE_DATA_OPTION = "jsonl"  # csv, db, json, jsonl, sqlite, mongodb, excel, postgres
```

### 8.2 Cấu hình database

```python
# config/db_config.py

# MySQL
MYSQL_DB_HOST = "localhost"
MYSQL_DB_PORT = 3306
MYSQL_DB_NAME = "media_crawler"

# Redis
REDIS_DB_HOST = "127.0.0.1"
REDIS_DB_PORT = 6379

# MongoDB
MONGODB_HOST = "localhost"
MONGODB_PORT = 27017

# SQLite
SQLITE_DB_PATH = "database/sqlite_tables.db"
```

---

## 9. Module tiện ích

### 9.1 Tổng quan hàm tiện ích

| Module | File | Chức năng chính |
|------|------|---------|
| App runner | `app_runner.py` | Signal, thoát nhẹ, dọn dẹp |
| Mở trình duyệt | `browser_launcher.py` | Phát hiện đường dẫn, mở process |
| Quản lý CDP | `cdp_browser.py` | Kết nối CDP, context trình duyệt |
| Tiện ích crawler | `crawler_util.py` | QR, captcha, User-Agent |
| Ghi file | `async_file_writer.py` | Ghi CSV/JSON bất đồng bộ, wordcloud |
| Slider | `slider_util.py` | Xử lý captcha kéo |
| Thời gian | `time_util.py` | Timestamp, ngày |

### 9.2 Quản lý chạy ứng dụng

```mermaid
flowchart TB
    Start([Khởi động]) --> Run["run(app_main, app_cleanup)"]
    Run --> Main["Chạy app_main()"]
    Main --> Running{Đang chạy}

    Running -->|Hoàn tất bình thường| Cleanup1["Chạy app_cleanup()"]
    Running -->|SIGINT/SIGTERM| Signal["Bắt tín hiệu"]

    First{Tín hiệu lần 1?}
    Signal --> First
    First -->|Có| Cleanup2["Bắt đầu dọn"]
    First -->|Không| Force["Thoát cưỡng bức"]

    Cleanup1 & Cleanup2 --> Cancel["Hủy task khác"]
    Cancel --> Wait["Chờ task xong<br/>(timeout 15 giây)"]
    Wait --> End([Thoát])
    Force --> End
```

---

## 10. Quan hệ phụ thuộc module

```mermaid
flowchart TB
    subgraph Entry["Tầng lối vào"]
        main["main.py"]
        config["config/"]
        cmdarg["cmd_arg/"]
    end

    subgraph Core["Tầng lõi"]
        base["base/base_crawler.py"]
        platforms["media_platform/*/"]
    end

    subgraph Client["Tầng client"]
        client["*/client.py"]
        login["*/login.py"]
    end

    subgraph Storage["Tầng lưu trữ"]
        store["store/"]
        database["database/"]
    end

    subgraph Infra["Hạ tầng"]
        proxy["proxy/"]
        cache["cache/"]
        tools["tools/"]
    end

    subgraph External["Phụ thuộc ngoài"]
        playwright["Playwright"]
        httpx["httpx"]
        sqlalchemy["SQLAlchemy"]
        motor["Motor/MongoDB"]
    end

    main --> config
    main --> cmdarg
    main --> Core

    Core --> base
    platforms --> base
    platforms --> Client

    client --> proxy
    client --> httpx
    login --> tools

    platforms --> Storage
    Storage --> sqlalchemy
    Storage --> motor

    client --> playwright
    tools --> playwright

    proxy --> cache
```

---

## 11. Hướng dẫn mở rộng

### 11.1 Thêm nền tảng mới

1. Tạo thư mục mới trong `media_platform/`
2. Implement các file lõi:
   - `core.py` — kế thừa `AbstractCrawler`
   - `client.py` — kế thừa `AbstractApiClient` và `ProxyRefreshMixin`
   - `login.py` — kế thừa `AbstractLogin`
   - `field.py` — enum nền tảng
3. Tạo thư mục lưu trữ tương ứng trong `store/`
4. Đăng ký trong `CrawlerFactory.CRAWLERS` của `main.py`

### 11.2 Thêm cách lưu mới

1. Tạo class implement mới trong `store/`
2. Kế thừa `AbstractStore`
3. Implement `store_content`, `store_comment`, `store_creator`
4. Đăng ký trong `StoreFactory.STORES` của từng nền tảng

### 11.3 Thêm nhà cung cấp proxy

1. Tạo class mới trong `proxy/providers/`
2. Kế thừa `BaseProxy`
3. Implement `get_proxy()`
4. Đăng ký trong cấu hình

---

## 12. Tham chiếu nhanh

### 12.1 Lệnh thường dùng

```bash
# Khởi động crawler
python main.py

# Chỉ định nền tảng
python main.py --platform xhs

# Chỉ định cách đăng nhập
python main.py --lt qrcode

# Chỉ định kiểu crawler
python main.py --type search
```

### 12.2 Đường dẫn file then chốt

| Mục đích | Đường dẫn |
|------|---------|
| Entry | `main.py` |
| Cấu hình lõi | `config/base_config.py` |
| Cấu hình DB | `config/db_config.py` |
| Lớp cơ sở crawler | `base/base_crawler.py` |
| Model ORM | `database/models.py` |
| Pool proxy | `proxy/proxy_ip_pool.py` |
| Trình duyệt CDP | `tools/cdp_browser.py` |

---

*Trend Radar — crawler kế thừa MediaCrawler. Tài liệu WebUI: [webui-guide.md](webui-guide.md).*
