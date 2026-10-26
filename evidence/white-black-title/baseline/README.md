# Đảo Mật Mã · CMC Infrasec × NextFest 26

Game săn kho báu CTF tiếng Việt cho người mới: **5 màn**, Easy/Hard riêng, guest nhập tên, bảng xếp hạng SQLite, hướng dẫn và bàn giải mã tại trình duyệt. Giải đủ 5 flag để mở mã hoàn thành và nhận **sticker logo CMC Infrasec tại NextFest 26**.

## Chạy trên Windows / PowerShell

Yêu cầu Node.js 22+ và Python 3.11+. Tại `L:\ctf-chall`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
npm ci
npm run build
.\scripts\start.ps1
```

Mở **http://127.0.0.1:3000**. Dừng bằng `.\scripts\stop.ps1`. API chỉ lắng nghe loopback tại port 8000. Log ở `evidence/runtime/`.

Để phát triển, mở hai terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
# terminal thứ hai
npm run dev
```

## Luật chơi

| Màn | Kỹ năng | Weight | Easy | Hard |
|---|---|---:|---|---|
| Chai thư | Encoding | 2 | Base64 | Base64 + hex |
| La bàn | Crypto | 4 | Caesar 3 | Tự xác định Caesar |
| Đài quan sát | Web | 6 | Bình luận HTML | Thuộc tính + Base64, có mồi nhử |
| Hải đăng | Forensics | 8 | Ghép log theo thứ tự | Metadata PNG + hex |
| Hang cuối | Crypto/Misc | 10 | XOR hex | XOR Base64, khóa từ hải đăng |

Flag có dạng `DAO{...}`, phân biệt hoa thường. Điểm = weight × 100 − 25 × số gợi ý, tối đa 3.000/mode. Sai flag không trừ điểm. Mỗi lần đúng chỉ nhận điểm một lần. BXH xếp số màn → điểm → thời gian hoàn thành. Đồng hồ của từng mode bắt đầu từ lúc mở manh mối đầu tiên. Thời gian không dừng khi đóng trình duyệt.

Tên và điểm là dữ liệu công khai; tên có thể trùng, không phải tài khoản đã xác minh. Cookie giữ phiên 30 ngày. Đổi trình duyệt/xóa cookie mất quyền tiếp tục phiên cũ. “Chuyến đi mới” giữ hàng cũ trên BXH và tạo bộ flag mới.

## Logo chính thức đã cài

Hai ảnh người dùng cung cấp được lưu nguyên byte tại `assets/branding/originals/`:
- `club-primary-original.png`: bản chính, nền đen/chữ trắng.
- `club-alternative-original.jpg`: bản thay thế, nền trắng/chữ đen.

Bản dùng trên web là `public/club-logo.png` (PNG 1024×1024, thu nhỏ bản chính) và `public/club-logo-light.jpg` (bản JPEG thay thế nguyên gốc). Header, footer và màn nhận thưởng dùng bản trắng ở giao diện sáng, bản đen ở giao diện tối. Giữ toàn bộ bố cục vuông, không cắt, không đảo màu, không tách nền; Next.js tự tối ưu kích thước tải về.

Palette sáng: trắng ngà, mực xanh rừng, biển xanh xám và CTA đất nung. Palette tối: xanh than gần đen, chữ trắng ngà và CTA cam đào. Kiểm tra contrast bằng `.\.venv\Scripts\python.exe scripts/check_palette.py`; kết quả chi tiết trong `evidence/logo-update/palette-contrast.json`.

Sau khi thay ảnh trong public, chạy build và khởi động lại:

```powershell
npm run build
.\scripts\stop.ps1
.\scripts\start.ps1
```

Mã hoàn thành `NF26-…` được server cấp sau 5 màn. Ban tổ chức kiểm tra và phát sticker trực tiếp; ứng dụng không giả định sticker đã được trao. Tra mã trên máy chủ:

```powershell
.\.venv\Scripts\python.exe scripts/check_reward.py NF26-MA-HOAN-THANH
```

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
npm audit
.\.venv\Scripts\python.exe -m pip_audit -r backend/requirements.txt
```

E2E tự tạo SQLite riêng ở `.scratch/`, dùng port 3100/8100, không trộn điểm thử với dữ liệu thật. Ảnh kiểm tra 320/375/414/768/1440, sáng/tối, ở `evidence/screenshots/`. Chạy production build trước E2E. Cấu hình Playwright hiện là Windows.

## Cấu hình máy chủ

- `DATABASE_PATH`: mặc định `backend/data/game.sqlite3`; lưu trên ổ bền vững, sao lưu file SQLite khi dừng API.
- `BACKEND_URL`: upstream cố định của Next.js; mặc định `http://127.0.0.1:8000`.
- `APP_ORIGINS`: cùng danh sách origin đầy đủ ở cả Next.js và Python, ngăn cách bằng dấu phẩy, không có dấu `/` cuối. Mặc định localhost/127.0.0.1 port 3000.
- `COOKIE_SECURE=1` khi dùng HTTPS. Chạy một API instance; không chia file SQLite qua ổ mạng.
- Khi tổ chức công khai, TLS/reverse proxy ở phía trước Next.js; giữ port API nội bộ. Script start dành cho bản local, đặt origin local rõ ràng.

## Hồ sơ bàn giao

`docs/session-review.md`, `docs/security-review.md`, `docs/openapi.json`, `evidence/logo-update/VERIFICATION.txt`, `evidence/logo-update/DIFF_FILE.patch`, `evidence/logo-update/ROLLBACK.sh`. Bản gốc cùng hash nằm trong `evidence/baseline/` và `evidence/original-hashes.json`. Rollback chỉ khôi phục mã nguồn, không xóa SQLite, logo được gửi sau hay dữ liệu người chơi.
