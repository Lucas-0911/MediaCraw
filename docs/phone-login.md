# Ghi chú đăng nhập bằng số điện thoại + mã OTP

CLI `--lt phone` cũng ghi trong [handbook/usage.md](handbook/usage.md). Không khuyến nghị.

Quy trình phức tạp, không khuyến nghị. Ưu tiên QR + CDP.

Khi trình duyệt giả lập đăng nhập SĐT, phần mềm chuyển tiếp SMS gửi OTP về crawler để điền tự động.

Chuẩn bị:

- Máy Android + [SmsForwarder](https://github.com/pppscn/SmsForwarder)
- WEBHOOK trỏ tới `recv_sms.py` (cần tunnel nếu máy không public, ví dụ [ngrok](https://ngrok.com/docs/))
- Redis
- Chạy `uv run python recv_sms.py`, rồi `uv run main.py --platform dy --lt phone`
