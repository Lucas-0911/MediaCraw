## Tài liệu Kuaidaili (hỗ trợ cá nhân và doanh nghiệp)

Đăng ký tại [Kuaidaili](https://www.kuaidaili.com/) (ở Trung Quốc dùng IP proxy cần xác thực danh tính). Chọn **private proxy (私密代理)**.

Khởi tạo trong `proxy/providers/kuaidl_proxy.py`:

```python
def new_kuai_daili_proxy() -> KuaiDaiLiProxy:
    return KuaiDaiLiProxy(
        kdl_secret_id=os.getenv("kdl_secret_id", "secret_id Kuaidaili của bạn"),
        kdl_signature=os.getenv("kdl_signature", "chữ ký Kuaidaili của bạn"),
        kdl_user_name=os.getenv("kdl_user_name", "tên đăng nhập Kuaidaili"),
        kdl_user_pwd=os.getenv("kdl_user_pwd", "mật khẩu Kuaidaili"),
    )
```

Bốn giá trị lấy từ đơn dùng thử / console Kuaidaili: `kdl_user_name`, `kdl_user_pwd`, `kdl_secret_id`, `kdl_signature`.
