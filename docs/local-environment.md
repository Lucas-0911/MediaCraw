# Quản lý môi trường local

## Phương án khuyến nghị: uv

### 1. Điều kiện tiên quyết
- Cài [uv](https://docs.astral.sh/uv/getting-started/installation), kiểm tra bằng `uv --version`.
- Python khuyến nghị **3.11** (dependency hiện tại xây trên phiên bản này).
- Cài Node.js (cần cho Douyin, Zhihu, …), phiên bản `>= 16.0.0`.

### 2. Đồng bộ dependency Python
```shell
# Vào thư mục gốc dự án
cd MediaCrawler

# Dùng uv để thống nhất phiên bản Python và dependency
uv sync
```

### 3. Cài trình điều khiển trình duyệt Playwright
```shell
uv run playwright install
```
> Dự án đã hỗ trợ Playwright kết nối Chrome local. Nếu dùng CDP, chỉnh cấu hình liên quan `xhs` và `dy` trong `config/base_config.py`.

### 4. Chạy crawler
```shell
# Mặc định chưa bật crawl comment; nếu cần comment, sửa ENABLE_GET_COMMENTS trong config/base_config.py
# Các công tắc khác cũng nằm trong config/base_config.py

# Đọc từ khóa từ config, crawl bài viết và comment
uv run main.py --platform xhs --lt qrcode --type search

# Đọc danh sách ID bài viết từ config, crawl bài viết và comment
uv run main.py --platform xhs --lt qrcode --type detail

# Ví dụ nền tảng khác
uv run main.py --help
```

## Phương án dự phòng: venv Python thuần (không khuyến nghị)

### Tạo và kích hoạt môi trường ảo
> Nếu crawl Douyin hoặc Zhihu, cần cài Node.js trước, phiên bản `>= 16`.
```shell
# Vào thư mục gốc dự án
cd MediaCrawler

# Tạo môi trường ảo (ví dụ Python 3.11, requirements xây trên phiên bản này)
python -m venv venv

# Kích hoạt trên macOS & Linux
source venv/bin/activate

# Kích hoạt trên Windows
venv\Scripts\activate
```

### Cài dependency và driver
```shell
pip install -r requirements.txt
playwright install
```

### Chạy crawler (venv)
```shell
# Đọc từ khóa từ config, crawl bài viết và comment
python main.py --platform xhs --lt qrcode --type search

# Đọc danh sách ID bài viết từ config, crawl bài viết và comment
python main.py --platform xhs --lt qrcode --type detail

# Thêm ví dụ
python main.py --help
```
