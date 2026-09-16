# Hướng dẫn xuất Excel

## Tổng quan

MediaCrawler hỗ trợ xuất dữ liệu đã crawl ra file Excel (.xlsx) có định dạng, nhiều sheet cho nội dung, comment và creator.

## Tính năng

- **Workbook nhiều sheet**: tách Contents, Comments, Creators
- **Định dạng chuyên nghiệp**:
  - Header nền xanh, chữ trắng
  - Tự chỉnh độ rộng cột
  - Viền ô và xuống dòng
  - Bố cục dễ đọc
- **Xuất thông minh**: sheet trống bị bỏ
- **Lưu có tổ chức**: file vào `data/{platform}/` kèm timestamp

## Cài đặt

Xuất Excel cần thư viện `openpyxl`:

```bash
# Dùng uv (khuyến nghị)
uv sync

# Hoặc pip
pip install openpyxl
```

## Cách dùng

### Cơ bản

1. **Bật xuất Excel** trong `config/base_config.py`:

```python
SAVE_DATA_OPTION = "excel"  # Đổi từ jsonl/json/csv/db sang excel
```

2. **Chạy crawler**:

```bash
# Ví dụ Xiaohongshu
uv run main.py --platform xhs --lt qrcode --type search

# Ví dụ Douyin
uv run main.py --platform dy --lt qrcode --type search

# Ví dụ Bilibili
uv run main.py --platform bili --lt qrcode --type search
```

3. **Tìm file Excel** trong `data/{platform}/`:
   - Tên file: `{platform}_{crawler_type}_{timestamp}.xlsx`
   - Ví dụ: `xhs_search_20250128_143025.xlsx`

### Ví dụ dòng lệnh

```bash
# Tìm theo từ khóa, xuất Excel
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# Crawl bài chỉ định, xuất Excel
uv run main.py --platform xhs --lt qrcode --type detail --save_data_option excel

# Crawl trang creator, xuất Excel
uv run main.py --platform xhs --lt qrcode --type creator --save_data_option excel
```

## Cấu trúc file Excel

### Sheet Contents
Thông tin bài/video:
- `note_id`: ID bài
- `title`: tiêu đề
- `desc`: mô tả
- `user_id`: ID tác giả
- `nickname`: biệt danh
- `liked_count`: lượt thích
- `comment_count`: số comment
- `share_count`: lượt chia sẻ
- `ip_location`: vị trí IP
- `image_list`: URL ảnh, cách nhau bằng dấu phẩy
- `tag_list`: tag, cách nhau bằng dấu phẩy
- `note_url`: link bài
- Và các trường riêng từng nền tảng...

### Sheet Comments
Thông tin comment:
- `comment_id`: ID comment
- `note_id`: ID bài liên quan
- `content`: nội dung
- `user_id`: ID người comment
- `nickname`: biệt danh
- `like_count`: lượt thích comment
- `create_time`: thời điểm
- `ip_location`: vị trí
- `sub_comment_count`: số trả lời
- Và các trường khác...

### Sheet Creators
Thông tin creator:
- `user_id`: ID người dùng
- `nickname`: tên hiển thị
- `gender`: giới tính
- `avatar`: URL ảnh đại diện
- `desc`: bio
- `fans`: số follower
- `follows`: số đang follow
- `interaction`: tổng tương tác
- Và các trường khác...

## So với định dạng khác

### So với CSV
- Nhiều sheet trong một file
- Có định dạng
- Xử lý ký tự đặc biệt tốt hơn
- Tự chỉnh độ rộng cột
- Ít lỗi encoding

### So với JSON
- Bảng dễ đọc
- Mở được bằng Excel / Google Sheets
- Thuận cho phân tích
- Dễ chia sẻ với người không kỹ thuật

### So với database
- Không cần cài DB
- Một file, dễ mang đi
- Dễ chia sẻ và lưu trữ
- Dùng offline

## Mẹo

1. **Dữ liệu lớn**: crawl > 10.000 dòng nên dùng database cho hiệu năng tốt hơn.

2. **Phân tích**: file Excel dùng tốt với:
   - Microsoft Excel
   - Google Sheets
   - LibreOffice Calc
   - Python pandas: `pd.read_excel('file.xlsx')`

3. **Gộp dữ liệu**:

   ```python
   import pandas as pd
   df1 = pd.read_excel('file1.xlsx', sheet_name='Contents')
   df2 = pd.read_excel('file2.xlsx', sheet_name='Contents')
   combined = pd.concat([df1, df2])
   combined.to_excel('combined.xlsx', index=False)
   ```

4. **Dung lượng**: Excel thường lớn hơn CSV 2–3 lần nhưng nhỏ hơn JSON.

## Xử lý sự cố

### Lỗi "openpyxl not installed"

```bash
uv add openpyxl
# hoặc
pip install openpyxl
```

### Không tạo được file Excel

Kiểm tra:
1. `SAVE_DATA_OPTION = "excel"` trong config
2. Crawler đã thu thập được dữ liệu
3. Console không có lỗi
4. Thư mục `data/{platform}/` tồn tại

### File Excel trống

Thường vì:
- Không crawl được dữ liệu (kiểm tra từ khóa/ID)
- Đăng nhập thất bại
- Nền tảng chặn request (IP / rate limit)

## Ví dụ output

Sau khi crawl thành công:

```
[ExcelStoreBase] Initialized Excel export to: data/xhs/xhs_search_20250128_143025.xlsx
[ExcelStoreBase] Stored content to Excel: 7123456789
[ExcelStoreBase] Stored comment to Excel: comment_123
...
[Main] Excel file saved successfully
```

File Excel sẽ có:
- Header xanh
- Viền rõ
- Wrap text cho nội dung dài
- Cột tự co
- Sheet tách theo loại dữ liệu

## Nâng cao

### Gọi từ code

```python
from store.excel_store_base import ExcelStoreBase

# Tạo store
store = ExcelStoreBase(platform="xhs", crawler_type="search")

# Ghi dữ liệu
await store.store_content({
    "note_id": "123",
    "title": "Test Post",
    "liked_count": 100
})

# Lưu file
store.flush()
```

### Tùy chỉnh định dạng

Kế thừa `ExcelStoreBase`:

```python
from store.excel_store_base import ExcelStoreBase

class CustomExcelStore(ExcelStoreBase):
    def _apply_header_style(self, sheet, row_num=1):
        super()._apply_header_style(sheet, row_num)
        # Thêm tùy chỉnh tại đây
```

## Hỗ trợ

Khi gặp vấn đề:
- Xem [Câu hỏi thường gặp](faq.md)
- Mở issue trên GitHub
- Tham gia nhóm WeChat

---

**Lưu ý**: Xuất Excel chỉ phục vụ học tập và nghiên cứu. Tôn trọng điều khoản nền tảng và giới hạn tần suất request.
