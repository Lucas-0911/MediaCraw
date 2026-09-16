# Các lỗi thường gặp khi chạy chương trình

## Thiếu môi trường Node

Hỏi: Crawl Douyin và Zhihu báo lỗi: `execjs._exceptions.ProgramError: SyntaxError: 缺少 ';'`  
Đáp: Thiếu môi trường Node.js. Cài Node.js phiên bản `>= v16`.

Hỏi: Dùng Cookie crawl Douyin báo: `execjs._exceptions.ProgramError: TypeError: Cannot read property 'JS_MD5_NO_COMMON_JS' of null`  
Đáp: Trên Windows, tải [Node.js v16.8.0 Windows 64-bit Installer](https://nodejs.org/en/blog/release/v16.8.0), next tới khi xong.

## Xiaohongshu: slider mãi không qua

Hỏi: Quét mã đăng nhập Xiaohongshu thành công rồi trình duyệt cứ kẹt slider, không vào được?  
Đáp: Xiaohongshu kiểm soát rất chặt. **Nên dùng chế độ CDP gắn trình duyệt thật của bạn** (cấu hình mặc định), đừng dùng ẩn danh hay Playwright chuẩn. Trình duyệt thật tái sử dụng Cookie, phiên đăng nhập và lịch sử, giảm xác suất bị phát hiện. Nếu vẫn kẹt slider, xóa thư mục `brower_data` trong dự án rồi đăng nhập lại.

## Chỉ định từ khóa

Hỏi: Có chỉ định từ khóa crawl được không?  
Đáp: Trong `config/base_config.py`, tham số `KEYWORDS` điều khiển từ khóa cần crawl.

## Chỉ định bài viết

Hỏi: Có chỉ định bài viết được không?  
Đáp: Trong `config/base_config.py`, `XHS_SPECIFIED_ID_LIST` là danh sách ID bài cần crawl.

## Crawl bị hết hiệu lực

Hỏi: Lúc đầu crawl được, một lúc sau thì hỏng?  
Đáp: Thường do tài khoản bị cơ chế chống spam của nền tảng. **Đừng crawl quy mô lớn**, sẽ ảnh hưởng nền tảng.

## Đổi tài khoản khác

Hỏi: Đổi tài khoản đăng nhập thế nào?  
Đáp: Xóa thư mục `brower_data/` ở thư mục gốc dự án.

## Playwright timeout

Hỏi: Báo `playwright._impl._api_types.TimeoutError: Timeout 30000ms exceeded.`  
Đáp: Kiểm tra xem có đang bật VPN/proxy không.

## Cấu hình Playwright để tự qua slider

Hỏi: Sau khi quét mã Xiaohongshu thành công, xác minh thủ công thế nào?  
Đáp: Mở `config/base_config.py`, đặt `HEADLESS = False`, khởi động lại, rồi tự qua captcha trên trình duyệt.

## Tạo wordcloud

Hỏi: Cấu hình tạo wordcloud thế nào?  
Đáp: Trong `config/base_config.py`, đặt cả `ENABLE_GET_WORDCLOUD` và `ENABLE_GET_COMMENTS` thành `True`.

## Thêm stopword và cụm từ tùy chỉnh cho wordcloud

Hỏi: Thêm stopword và cụm từ tùy chỉnh thế nào?  
Đáp: Mở `docs/hit_stopwords.txt`, mỗi từ một dòng. Trong `config/base_config.py`, thêm vào `CUSTOM_WORDS` theo đúng format.

## CDP kết nối trình duyệt có sẵn

Hỏi: Chạy crawler báo không kết nối được trình duyệt, `Cannot connect to existing browser on port 9222`?  
Đáp: Kiểm tra:
1. Chrome đã mở và đang chạy
2. Vào `chrome://inspect/#remote-debugging`, bật **"Allow remote debugging for this browser instance"**
3. Trang phải hiện `Server running at: 127.0.0.1:9222`; nếu không thì remote debug chưa bật
4. Chrome `>= 144` (bản thấp không hỗ trợ). Xem phiên bản tại `chrome://version`

Hỏi: Chạy crawler thì trình duyệt hiện hộp xác nhận, phải làm gì?  
Đáp: Bình thường. Chrome hiện hộp xác nhận khi kết nối trình duyệt đang mở — bấm Accept. Chương trình chờ tối đa 60 giây.

Hỏi: Không muốn gắn trình duyệt đang mở, muốn chương trình tự mở trình duyệt mới?  
Đáp: Trong `config/base_config.py` đặt `CDP_CONNECT_EXISTING = False`; chương trình sẽ tự phát hiện và mở Chrome/Edge mới.

Hỏi: Vì sao nên gắn trình duyệt đang có thay vì mở mới?  
Đáp: Gắn trình duyệt đang dùng tái sử dụng Cookie thật, phiên đăng nhập, extension và lịch sử — nền tảng khó phân biệt automation với người dùng thật, **giảm mạnh rủi ro bị chặn**. Trình duyệt mới là môi trường “sạch”, dễ bị nhận là crawler.
