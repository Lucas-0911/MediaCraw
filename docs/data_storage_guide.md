# Hướng dẫn lưu dữ liệu

### Lưu dữ liệu

MediaCrawler hỗ trợ nhiều cách lưu; chọn phương án phù hợp nhu cầu:

#### Cách lưu

- **CSV**: lưu vào `data/`
- **JSON**: lưu vào `data/`
- **JSONL**: lưu vào `data/` — định dạng mặc định, mỗi dòng một object JSON, append tốt
- **Excel**: file Excel đã định dạng trong `data/`
  - Nhiều sheet (nội dung, comment, creator)
  - Header, độ rộng cột, viền
  - Dễ phân tích và chia sẻ
- **Database**
  - `--init_db` để khởi tạo (khi dùng `--init_db` không cần tham số tùy chọn khác)
  - **SQLite**: nhẹ, không cần server, phù hợp dùng cá nhân (khuyến nghị)
    1. Khởi tạo: `--init_db sqlite`
    2. Lưu: `--save_data_option sqlite`
  - **MySQL**: lưu vào MySQL (cần tạo database trước)
    1. Khởi tạo: `--init_db mysql`
    2. Lưu: `--save_data_option db` (`db` giữ để tương thích lịch sử)
  - **PostgreSQL**: CSDL quan hệ nâng cao (khuyến nghị production)
    1. Khởi tạo: `--init_db postgres`
    2. Lưu: `--save_data_option postgres`

#### Ví dụ

```shell
# Lưu Excel (phù hợp phân tích dữ liệu)
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# Khởi tạo SQLite
uv run main.py --init_db sqlite
# Lưu SQLite
uv run main.py --platform xhs --lt qrcode --type search --save_data_option sqlite
```

```shell
# Khởi tạo MySQL
uv run main.py --init_db mysql
# Lưu MySQL (giữ tham số db vì tương thích cũ)
uv run main.py --platform xhs --lt qrcode --type search --save_data_option db
```

```shell
# Khởi tạo PostgreSQL
uv run main.py --init_db postgres
# Lưu PostgreSQL
uv run main.py --platform xhs --lt qrcode --type search --save_data_option postgres
```

```shell
# Lưu CSV
uv run main.py --platform xhs --lt qrcode --type search --save_data_option csv

# Lưu JSON
uv run main.py --platform xhs --lt qrcode --type search --save_data_option json

# Lưu JSONL (mặc định, có thể không cần chỉ định)
uv run main.py --platform xhs --lt qrcode --type search --save_data_option jsonl
```

#### Tài liệu chi tiết

- **Xuất Excel**: [Hướng dẫn xuất Excel](excel_export_guide.md)
- **Cấu hình database**: [Câu hỏi thường gặp](faq.md)
