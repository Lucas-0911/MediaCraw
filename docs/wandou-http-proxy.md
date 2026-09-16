## Tài liệu proxy Wandou HTTP (chỉ hỗ trợ doanh nghiệp)

Đăng ký tại [Wandou HTTP](https://h.wandouip.com/). Ở Trung Quốc dùng IP proxy cần xác thực danh tính.

Khởi tạo trong `proxy/providers/wandou_http_proxy.py`, cần `app_key`:

```python
def new_wandou_http_proxy() -> WanDouHttpProxy:
    return WanDouHttpProxy(
        app_key=os.getenv("wandou_app_key", "app_key Wandou HTTP của bạn"),
    )
```

`app_key` nằm trong trang cá nhân, mục Open API (`开放接口`).
