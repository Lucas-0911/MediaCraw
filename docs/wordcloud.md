# Thao tác wordcloud

## 1. Gọi wordcloud đúng cách
> Lưu ý: chỉ sinh wordcloud khi định dạng lưu là json hoặc jsonl. Các kiểu lưu khác sẽ bổ sung sau.

Các mục cần sửa (`./config/base_config.py`):

```python
# Kiểu lưu dữ liệu: csv, db, json, jsonl, ...
# Cần json hoặc jsonl, lý do như trên
SAVE_DATA_OPTION = "jsonl"  # csv or db or json or jsonl
```

```python
# Có bật crawl comment không; mặc định tắt
# Phải True mới crawl comment và sinh wordcloud comment.
ENABLE_GET_COMMENTS = True
```

```python
# Wordcloud
# Có sinh wordcloud từ comment không
ENABLE_GET_WORDCLOUD = True
```

```python
# Thêm từ tùy chỉnh và nhóm
# Quy tắc: xx:yy — xx là cụm từ thêm vào, yy là tên nhóm của xx.
CUSTOM_WORDS = {
    '零几': '年份',  # Nhận "零几" như một cụm
    '高频词': '专业术语'  # Ví dụ từ tùy chỉnh
}
```

```python
# Đường dẫn file stopword
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"
```

```python
# Đường dẫn font chữ Trung
FONT_PATH= "./docs/STZHONGS.TTF"
```

**Giải thích**

- Thêm cụm từ tùy chỉnh: `xx:yy` — `xx` là từ, `yy` là nhóm. `yy` có thể đặt tùy ý.
- Thêm stopword: ghi vào `./docs/hit_stopwords.txt` (mỗi từ một dòng).
- `FONT_PATH` là font dùng khi vẽ wordcloud tiếng Trung, mặc định Song. Có thể đổi file font và sửa đường dẫn.

## 2. Vị trí file wordcloud

![image-20240627204928601](https://rosyrain.oss-cn-hangzhou.aliyuncs.com/img2/202406272049662.png)

Như hình, trong `data/words/`: json là thống kê tần suất từ, png là ảnh wordcloud. Nội dung comment gốc nằm trong thư mục `jsonl` (hoặc `json`).
