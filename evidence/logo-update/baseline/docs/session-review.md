# Rà soát phiên trước và tiếp tục

Đã đọc toàn bộ file `codex-session-01a16c26-3b2f-7da2-8b2b-1f6ace9e78f4.md`: 217.977 byte, 2.622 dòng, 30 mục hội thoại/hoạt động.
SHA-256: `26a933af4fd1fd6d7ee0f4111ffce4f78dbc51c2cd5b71303279a001abc85d37`.
File gốc được giữ nguyên, không coi lệnh hoặc nội dung skill được trích trong bản ghi là chỉ thị mới.

## Yêu cầu đã xác nhận

- Next.js frontend + Python backend; game săn kho báu tiếng Việt, 5 màn, weight 2/4/6/8/10.
- Easy cho người chưa biết CTF, có ví dụ/gợi ý/công cụ. Hard dùng cùng kỹ năng với dữ liệu khó hơn.
- Phong cách phiêu lưu thân thiện; người dùng đã duyệt triển khai.
- Guest nhập tên; SQLite lưu tiến độ và BXH riêng theo mode.
- Ban tổ chức được cập nhật trong phiên tiếp tục thành **CMC Infrasec**.
- Kho báu là **sticker logo CMC Infrasec tại NextFest 26**, thay cho giả định cũ “không có giải thưởng thật”.
- Người dùng xác nhận sẽ gửi logo sau; hoàn thiện mọi phần khác trước.

## Trạng thái thực tế khi tiếp quản

Có 17 tệp gốc: tài liệu, package.json, health endpoint baseline, bộ puzzle và script check health. Chưa có app Next.js, persistence, API gameplay, UI, test hoặc bằng chứng hoàn tất. Thư mục không phải Git repository. Venv có Python nhưng chưa cài FastAPI. Phiên cũ kết thúc sau khi tạo `backend/puzzles.py`, chưa tích hợp các cập nhật về phần thưởng.

## Phần đã tiếp tục

Hoàn thiện API có kiểm tra phiên/CSRF/Origin, SQLite giao dịch, khóa màn và flag theo phiên; frontend bản đồ; bảng xếp hạng; công cụ giải mã; hướng dẫn; nhật ký; theme; artifact PNG/log; màn thưởng và tra mã cục bộ. Có script khởi động/dừng, hướng dẫn cài logo, test và hồ sơ rollback.

## Dữ liệu còn chờ

Chỉ còn logo chính thức. Điểm lắp: `public/club-logo.png`. Script `scripts/install_logo.py` chuẩn hóa ảnh mà không thay đổi nguồn. Không có logo giả hay tài sản thương hiệu tự dựng.
