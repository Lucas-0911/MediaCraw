# Hướng dẫn chế độ CDP

Vận hành tổng: [handbook/usage.md](handbook/usage.md). Kiến trúc CDP: [handbook/architecture.md](handbook/architecture.md) § hạ tầng.

## Tổng quan

CDP (Chrome DevTools Protocol) là kỹ thuật chống phát hiện nâng cao: điều khiển Chrome/Edge mà người dùng đang cài để crawl. So với automation Playwright truyền thống, CDP có các ưu điểm sau.

### Ưu điểm chính

1. **Môi trường trình duyệt thật**: dùng trình duyệt đã cài, gồm extension, plugin và cài đặt cá nhân
2. **Chống phát hiện tốt hơn**: fingerprint gần người dùng thật, khó bị nhận là tool tự động
3. **Giữ trạng thái người dùng**: kế thừa phiên đăng nhập, Cookie và lịch sử
4. **Hỗ trợ extension**: dùng được adblocker, extension proxy, …
5. **Hành vi tự nhiên hơn**: pattern gần người dùng thật

### Hai kiểu CDP

| Chế độ | Mô tả | Khi nào dùng |
|------|------|----------|
| **Gắn trình duyệt đang mở** (mặc định, khuyến nghị) | Kết nối Chrome đang dùng, tái sử dụng Cookie, extension và lịch sử thật | Cần chống phát hiện tối đa, giảm rủi ro bị chặn |
| **Mở trình duyệt mới** | Tự phát hiện và mở instance Chrome/Edge mới | Không cần tái sử dụng trạng thái trình duyệt |

## Bắt đầu nhanh

### Cách 1: gắn trình duyệt đang mở (mặc định, khuyến nghị)

Đây là **cách mặc định và nên dùng**: gắn thẳng Chrome đang dùng, chống phát hiện tốt nhất.

#### Bước 1: phiên bản Chrome

Cần Chrome **144 trở lên** (các bản ổn định từ tháng 1/2026 đều hỗ trợ). Xem tại `chrome://version`.

Nếu thấp hơn, tải bản mới tại [trang Chrome](https://www.google.com/chrome/).

#### Bước 2: bật remote debugging

1. Thanh địa chỉ Chrome: `chrome://inspect/#remote-debugging`
2. Bật **"Allow remote debugging for this browser instance"**
3. Trang hiện `Server running at: 127.0.0.1:9222` là đã sẵn sàng

#### Bước 3: chạy crawler

```bash
uv run main.py --platform xhs --lt qrcode --type search
```

Chrome sẽ **hiện hộp xác nhận** — bấm Accept. Chương trình chờ tối đa 60 giây.

#### Cấu hình

Mặc định trong `config/base_config.py`:

```python
# Bật CDP
ENABLE_CDP_MODE = True

# Gắn trình duyệt đang mở (mặc định bật)
CDP_CONNECT_EXISTING = True

# Cổng debug CDP (trùng cổng trên trang chrome://inspect)
CDP_DEBUG_PORT = 9222
```

### Cách 2: mở trình duyệt mới

Nếu không muốn gắn trình duyệt đang mở, để chương trình tự mở instance mới:

```python
ENABLE_CDP_MODE = True
CDP_CONNECT_EXISTING = False  # Tắt gắn trình duyệt sẵn có, mở trình duyệt mới
```

## Chi tiết tùy chọn cấu hình

### Cơ bản

| Mục | Kiểu | Mặc định | Ý nghĩa |
|--------|------|--------|------|
| `ENABLE_CDP_MODE` | bool | True | Bật chế độ CDP |
| `CDP_CONNECT_EXISTING` | bool | True | Gắn trình duyệt đang mở (nên bật) |
| `CDP_DEBUG_PORT` | int | 9222 | Cổng debug CDP |
| `CDP_HEADLESS` | bool | False | Headless khi CDP |
| `AUTO_CLOSE_BROWSER` | bool | True | Đóng trình duyệt khi chương trình kết thúc |

### Nâng cao

| Mục | Kiểu | Mặc định | Ý nghĩa |
|--------|------|--------|------|
| `CUSTOM_BROWSER_PATH` | str | "" | Đường dẫn trình duyệt tùy chỉnh (chỉ khi mở trình duyệt mới) |
| `BROWSER_LAUNCH_TIMEOUT` | int | 60 | Timeout kết nối trình duyệt (giây) |

### Đường dẫn trình duyệt tùy chỉnh

Nếu tự phát hiện thất bại, chỉ định tay:

```python
# Windows
CUSTOM_BROWSER_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# macOS
CUSTOM_BROWSER_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Linux
CUSTOM_BROWSER_PATH = "/usr/bin/google-chrome"
```

## Trình duyệt được hỗ trợ

### Windows
- Google Chrome (Stable, Beta, Dev, Canary)
- Microsoft Edge (Stable, Beta, Dev, Canary)

### macOS
- Google Chrome (Stable, Beta, Dev, Canary)
- Microsoft Edge (Stable, Beta, Dev, Canary)

### Linux
- Google Chrome / Chromium
- Microsoft Edge

## Ví dụ dùng

### Cơ bản

```python
import asyncio
from playwright.async_api import async_playwright
from tools.cdp_browser import CDPBrowserManager

async def main():
    cdp_manager = CDPBrowserManager()

    async with async_playwright() as playwright:
        browser_context = await cdp_manager.launch_and_connect(
            playwright=playwright,
            user_agent="User-Agent tùy chỉnh",
            headless=False
        )

        page = await browser_context.new_page()
        await page.goto("https://example.com")

        # Thao tác crawl...

        await cdp_manager.cleanup()

asyncio.run(main())
```

### Trong crawler

CDP đã gắn vào mọi crawler nền tảng; chỉ cần bật config:

```python
# Trong config/base_config.py
ENABLE_CDP_MODE = True

# Chạy crawler bình thường
python main.py
```

## Xử lý sự cố

### Câu hỏi thường gặp

#### 1. Không phát hiện trình duyệt
**Lỗi**: `未找到可用的浏览器` (không tìm thấy trình duyệt)

**Cách xử lý**:
- Đảm bảo đã cài Chrome hoặc Edge
- Kiểm tra trình duyệt nằm đúng đường dẫn chuẩn
- Dùng `CUSTOM_BROWSER_PATH` để chỉ định đường dẫn

#### 2. Cổng bị chiếm
**Lỗi**: `无法找到可用的端口` (không tìm thấy cổng trống)

**Cách xử lý**:
- Đóng chương trình khác đang dùng cổng debug
- Đổi `CDP_DEBUG_PORT`
- Hệ thống sẽ tự thử cổng kế tiếp

#### 3. Timeout khi mở trình duyệt
**Lỗi**: `浏览器在30秒内未能启动` (trình duyệt không khởi động trong 30 giây)

**Cách xử lý**:
- Tăng `BROWSER_LAUNCH_TIMEOUT`
- Kiểm tra tài nguyên máy
- Đóng chương trình chiếm tài nguyên

#### 4. Kết nối CDP thất bại
**Lỗi**: `CDP连接失败`

**Cách xử lý**:
- Kiểm tra firewall
- Đảm bảo localhost truy cập được
- Thử khởi động lại trình duyệt

### Mẹo debug

#### 1. Bật log chi tiết
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 2. Test CDP thủ công
```bash
# Mở Chrome tay
chrome --remote-debugging-port=9222

# Gọi trang debug
curl http://localhost:9222/json
```

#### 3. Kiểm tra process trình duyệt
```bash
# Windows
tasklist | findstr chrome

# macOS/Linux
ps aux | grep chrome
```

## Thực hành tốt

### 1. Chống phát hiện
- Giữ `CDP_HEADLESS = False` để chống phát hiện tốt nhất
- Dùng User-Agent thật
- Tránh request quá dày

### 2. Hiệu năng
- Đặt `AUTO_CLOSE_BROWSER` hợp lý
- Tái sử dụng instance trình duyệt, đừng restart liên tục
- Theo dõi bộ nhớ

### 3. Bảo mật
- Đừng lưu Cookie nhạy cảm trên môi trường production
- Định kỳ dọn dữ liệu trình duyệt
- Bảo vệ quyền riêng tư người dùng

### 4. Tương thích
- Test nhiều phiên bản trình duyệt
- Có phương án fallback (Playwright chuẩn)
- Theo dõi thay đổi chống crawl của site đích

## Nguyên lý kỹ thuật

### Gắn trình duyệt đang mở (khuyến nghị)

1. **Người dùng bật remote debug**: tick tại `chrome://inspect/#remote-debugging`
2. **Kết nối WebSocket**: chương trình nối `ws://localhost:9222/devtools/browser`
3. **Người dùng xác nhận**: Chrome hiện hộp thoại, bấm Accept là kết nối xong
4. **Tích hợp Playwright**: `connectOverCDP` để điều khiển trình duyệt
5. **Tái sử dụng context**: dùng context sẵn có (Cookie, phiên đăng nhập, …)

> Khác CDP truyền thống: cách cũ mở trình duyệt mới bằng `--remote-debugging-port`, lấy WebSocket URL qua HTTP `/json/version`. Gắn trình duyệt đang mở thì nối WebSocket trực tiếp. Chrome mới (136+) không còn HTTP endpoint cho remote debug; cần người dùng xác nhận trên trình duyệt.

### Mở trình duyệt mới

1. **Phát hiện trình duyệt**: quét đường dẫn cài Chrome/Edge
2. **Khởi động process**: `--remote-debugging-port`
3. **Kết nối CDP**: lấy WebSocket URL qua HTTP rồi nối debug interface
4. **Tích hợp Playwright**: `connectOverCDP`
5. **Quản lý context**: tạo hoặc tái sử dụng browser context

Cả hai cách đều tránh cơ chế phát hiện WebDriver truyền thống. Gắn trình duyệt đang mở chống phát hiện tốt hơn vì dùng môi trường thật của người dùng.

## Nhật ký cập nhật

### v1.0.0
- Bản đầu
- Phát hiện Chrome/Edge trên Windows và macOS
- Gắn vào mọi crawler nền tảng
- Đủ tùy chọn cấu hình và xử lý lỗi

## Đóng góp

Issue và Pull Request để cải thiện CDP đều được chào đón.

## Giấy phép

Tính năng này theo giấy phép chung của dự án, chỉ dùng để học tập và nghiên cứu.
