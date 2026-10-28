# Đảo Mật Mã · CMC Infrasec × NextFest 26

Game săn kho báu CTF tiếng Việt cho người mới: **5 màn**, Easy/Hard riêng, guest nhập tên, bảng xếp hạng SQLite, hướng dẫn và bàn giải mã tại trình duyệt. Giải đủ 5 flag để mở mã hoàn thành và nhận **sticker logo CMC Infrasec tại NextFest 26**.

## Clone repository

```bash
git clone https://github.com/dodinhhoanganhcmc/CTF-Challenge-NF26.git
cd CTF-Challenge-NF26
```

Nhánh mặc định: `main`. Repo private cần đăng nhập GitHub hoặc SSH/deploy key trước. Clone lấy **những thay đổi đã commit và push**; các thay đổi còn ở working tree máy phát triển sẽ chưa có trên server. Giữ `package-lock.json` và `backend/requirements-lock.txt` trong Git để cài lại đúng phiên bản.

## Yêu cầu

- Node.js **24 LTS** + npm; Python **3.11+** (khuyến nghị 3.12 trên Ubuntu 24.04).
- Git; ổ lưu bền vững cho SQLite. Một instance API duy nhất; không đặt database trên network filesystem.
- Chạy local: Windows/PowerShell hoặc Linux. Chạy server: phần dưới dùng **Ubuntu 24.04, systemd, Nginx**.

## Chạy trên Windows / PowerShell

Sau khi clone, đứng trong thư mục `CTF-Challenge-NF26` (hoặc thư mục repo hiện tại, ví dụ `L:\ctf-chall`):

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

## Chạy local trên Linux

Trong thư mục repo:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-lock.txt
npm ci
npm run build
```

Mở hai terminal, đều có working directory là thư mục repo:

```bash
# Terminal 1: Python API
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

```bash
# Terminal 2: Next.js
BACKEND_URL=http://127.0.0.1:8000 npm run start
```

Mở `http://127.0.0.1:3000`. Dừng bằng Ctrl+C ở cả hai terminal. Script `scripts/start.ps1` và `scripts/stop.ps1` chỉ dành cho Windows/local; không dùng chúng để cấu hình domain production.

## Triển khai Ubuntu server: systemd + Nginx + HTTPS

Luồng: **Internet → HTTPS Nginx → Next.js 127.0.0.1:3000 → FastAPI 127.0.0.1:8000 → SQLite**. Không mở trực tiếp port 3000/8000 ra Internet.

Các lệnh dưới giả định server mới và người vận hành có `sudo`. Thay **mọi** `ctf.example.com` bằng domain thật; trỏ bản ghi DNS A/AAAA về server trước khi cấp chứng chỉ. Cấu hình này không cần Google/Facebook Auth hay API key ngoài.

### 1. Cài công cụ

```bash
sudo apt update
sudo apt install -y git curl ca-certificates python3 python3-venv nginx certbot python3-certbot-nginx

# Cài Node.js 24 LTS nếu máy chưa có Node 24.
curl -fsSL https://deb.nodesource.com/setup_24.x -o /tmp/nodesource-24.sh
sudo bash /tmp/nodesource-24.sh
sudo apt install -y nodejs

node --version
npm --version
python3 --version
command -v node  # service bên dưới dùng /usr/bin/node
```

### 2. Clone và build dưới user riêng

```bash
sudo useradd --system --create-home --home-dir /var/lib/ctfgame --shell /usr/sbin/nologin ctfgame
sudo install -d -o ctfgame -g ctfgame /opt/ctf-chall /var/lib/cmc-infrasec
sudo -u ctfgame git clone --branch main https://github.com/dodinhhoanganhcmc/CTF-Challenge-NF26.git /opt/ctf-chall
cd /opt/ctf-chall
sudo -u ctfgame python3 -m venv .venv
sudo -u ctfgame .venv/bin/python -m pip install -r backend/requirements-lock.txt
sudo -u ctfgame npm ci --include=dev
sudo -u ctfgame npm run build
```

Nếu user/thư mục đã có từ lần triển khai trước, bỏ qua `useradd`/`git clone` và dùng mục cập nhật. Repo private: cấu hình quyền clone cho user `ctfgame` trước, không nhúng token vào URL hoặc README. Các lệnh cài Node chỉ cần làm một lần.

### 3. Cấu hình môi trường cho cả hai service

```bash
sudo install -m 600 -o root -g root /dev/null /etc/cmc-infrasec.env
sudo tee /etc/cmc-infrasec.env > /dev/null <<'ENV'
NODE_ENV=production
BACKEND_URL=http://127.0.0.1:8000
APP_ORIGINS=https://ctf.example.com
DATABASE_PATH=/var/lib/cmc-infrasec/game.sqlite3
COOKIE_SECURE=1
ENV
```

`APP_ORIGINS` phải là origin HTTPS thật, không có `/` cuối. Nếu có nhiều hostname, liệt kê ngăn cách bằng dấu phẩy, không thêm khoảng trắng; Nginx và chứng chỉ cũng phải phục vụ các hostname đó. `COOKIE_SECURE=1` chỉ gửi cookie qua HTTPS. Database nằm **ngoài repo**, không bị thay khi pull/build. File `.env.example` chỉ là mẫu local; Python hiện không tự nạp `.env.local`.

### 4. Tạo hai systemd service

```bash
sudo tee /etc/systemd/system/cmc-infrasec-api.service > /dev/null <<'UNIT'
[Unit]
Description=CMC Infrasec FastAPI game server
After=network.target

[Service]
Type=simple
User=ctfgame
Group=ctfgame
WorkingDirectory=/opt/ctf-chall
EnvironmentFile=/etc/cmc-infrasec.env
ExecStart=/opt/ctf-chall/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/systemd/system/cmc-infrasec-web.service > /dev/null <<'UNIT'
[Unit]
Description=CMC Infrasec Next.js web server
After=network.target cmc-infrasec-api.service
Requires=cmc-infrasec-api.service

[Service]
Type=simple
User=ctfgame
Group=ctfgame
WorkingDirectory=/opt/ctf-chall
EnvironmentFile=/etc/cmc-infrasec.env
ExecStart=/usr/bin/node /opt/ctf-chall/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now cmc-infrasec-api cmc-infrasec-web
sudo systemctl status cmc-infrasec-api cmc-infrasec-web --no-pager
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:3000/api/v1/catalog
```

Health API phải trả `{"status":"ok","stages":5}`. Catalog phải hiển thị organizer `CMC Infrasec`. Nếu `command -v node` không phải `/usr/bin/node`, dùng đường dẫn Node tuyệt đối đúng trong `ExecStart`, rồi `daemon-reload`.

### 5. Reverse proxy và HTTPS

```bash
sudo tee /etc/nginx/sites-available/cmc-infrasec > /dev/null <<'NGINX'
server {
    listen 80;
    server_name ctf.example.com;
    client_max_body_size 8k;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
NGINX

sudo ln -sfn /etc/nginx/sites-available/cmc-infrasec /etc/nginx/sites-enabled/cmc-infrasec
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d ctf.example.com --redirect
sudo certbot renew --dry-run
curl --fail https://ctf.example.com/api/v1/catalog
```

Cho phép TCP 80/443 trong firewall của máy/cloud. Nếu dùng UFW, giữ rule SSH hiện tại trước khi bật firewall; không thêm rule public cho 3000/8000. Nginx chuyển hướng HTTP sang HTTPS sau bước Certbot. Khi đã có HTTPS, thử nhập guest, giải một bài, reload trang và kiểm tra BXH để xác nhận cookie/proxy/database hoạt động cùng nhau.

### 6. Vận hành, log, tra mã phần thưởng

```bash
sudo systemctl restart cmc-infrasec-api cmc-infrasec-web
sudo journalctl -u cmc-infrasec-api -u cmc-infrasec-web -n 100 --no-pager
sudo journalctl -u cmc-infrasec-web -f
# Dừng theo thứ tự web rồi API:
sudo systemctl stop cmc-infrasec-web cmc-infrasec-api
# Khởi động lại:
sudo systemctl start cmc-infrasec-api cmc-infrasec-web
```

Tra một mã hoàn thành thật, không thay đổi database:

```bash
cd /opt/ctf-chall
sudo -u ctfgame .venv/bin/python scripts/check_reward.py NF26-012345ABCDEF --database /var/lib/cmc-infrasec/game.sqlite3
```

Thay mã ví dụ bằng mã người chơi. `NOT_FOUND`/exit 1 nghĩa là không tìm thấy mã. Tên guest, điểm, lượt chơi, deadline và mã thưởng nằm trong SQLite; restart server không xóa chúng. Sau khi dữ liệu đã tồn tại, không chép một database mẫu đè lên.

### 7. Sao lưu và cập nhật

Ví dụ maintenance update có downtime ngắn; dừng API trước khi copy file SQLite để bảo đảm bản sao nhất quán:

```bash
sudo install -d -m 700 /var/backups/cmc-infrasec
sudo systemctl stop cmc-infrasec-web cmc-infrasec-api
if sudo test -f /var/lib/cmc-infrasec/game.sqlite3; then
    sudo cp -p /var/lib/cmc-infrasec/game.sqlite3 "/var/backups/cmc-infrasec/game-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
fi

cd /opt/ctf-chall
sudo -u ctfgame git rev-parse HEAD  # ghi lại commit để có thể quay lại
sudo -u ctfgame git pull --ff-only origin main
sudo -u ctfgame .venv/bin/python -m pip install -r backend/requirements-lock.txt
sudo -u ctfgame npm ci --include=dev
sudo -u ctfgame npm run build
# Chỉ khởi động khi cài/build thành công.
sudo systemctl start cmc-infrasec-api cmc-infrasec-web
curl --fail http://127.0.0.1:8000/health
curl --fail https://ctf.example.com/api/v1/catalog
```

Thực hiện lần lượt và dừng nếu một lệnh lỗi. Không chạy `git reset --hard`/xóa database để chữa lỗi build. Khi quay lại bản source cũ, giữ nguyên SQLite; thay đổi schema cần xem tài liệu migration tương ứng. Giữ backup bên ngoài repo và hạn chế quyền đọc vì có dữ liệu phiên người chơi.

### 8. Chẩn đoán nhanh

| Hiện tượng | Kiểm tra |
|---|---|
| Nginx 502 / API 503 | `systemctl status`, `journalctl`; API 8000 và web 3000 có lắng nghe loopback không |
| Guest/nộp flag trả 403 | `APP_ORIGINS` giống hệt URL HTTPS đang mở ở cả hai service; giữ header `Origin`, proxy `Host`; restart cả hai sau khi đổi env |
| Mất phiên sau request | Chạy đúng HTTPS với `COOKIE_SECURE=1`, không chuyển qua lại domain/localhost; cookie không được trình duyệt chặn |
| SQLite readonly / không tạo DB | User `ctfgame` cần ghi được `/var/lib/cmc-infrasec` và file DB; không chỉ cấp quyền riêng file vì SQLite cần sidecar |
| Mất điểm sau redeploy | Kiểm tra `DATABASE_PATH` vẫn cùng đường dẫn bền vững; không tạo DB khác theo release |
| Node/Python không tìm thấy | Đường dẫn tuyệt đối `ExecStart`; `node --version`, `.venv/bin/python --version` |
| Logo/font lỗi sau cập nhật | Có `public/` và `assets/`, đã build/restart; kiểm tra request `/fonts/poppins-700.woff2` |

## `.gitignore` và dữ liệu trong Git

Đã bỏ qua dependencies, build/cache, `.env` thật, private-key files, SQLite/sidecar/backup, log, báo cáo test, evidence và transcript cục bộ. Vẫn giữ `.env.example`, source, `docs/`, `.scratch/` issue Markdown, logo/font và hai lockfile.

`.gitignore` chỉ ngăn **file chưa track**. File đã commit trước đó vẫn được Git theo dõi. Kiểm tra trước khi push:

```bash
git status --short
git ls-files -ci --exclude-standard
# Xem rule áp dụng kể cả khi file đã track:
git check-ignore --no-index -v backend/data/game.sqlite3
```

Nếu đã track evidence/transcript từ trước và muốn ngừng track, dùng `git rm --cached` cho **đúng đường dẫn đã kiểm tra**, rồi commit thay đổi index; file local vẫn giữ. Việc ignore không xóa dữ liệu khỏi lịch sử Git.

## Luật chơi

| Màn | Kỹ năng | Weight | Easy | Hard |
|---|---|---:|---|---|
| Chai thư | Encoding | 2 | Base64 | Base64 + hex |
| La bàn | Crypto | 4 | Caesar 3 | Tự xác định Caesar |
| Đài quan sát | Web | 6 | Bình luận HTML | Thuộc tính + Base64, có mồi nhử |
| Hải đăng | Forensics | 8 | Ghép log theo thứ tự | Metadata PNG + hex |
| Hang cuối | Crypto/Misc | 10 | XOR hex | XOR Base64, khóa từ hải đăng |

Flag có dạng `DAO{...}`, phân biệt hoa thường. Mỗi bài **Easy có 180 giây (3 phút), Hard có 420 giây (7 phút)**. Đồng hồ bắt đầu khi mở manh mối bài lần đầu; tải lại trang, đổi mode, đóng tab hay mở tab khác không tạm dừng hoặc cấp lại thời gian. Bài tiếp theo chỉ bắt đầu tính giờ khi được mở. Mỗi mode giữ đồng hồ riêng.

**Điểm theo thời gian (server tính):** gọi `B = weight × 100`, `T = 180/420`, `e = floor(số giây đã dùng)`, `h = số gợi ý`.

```text
điểm = max(0, B/2 + floor(B × (T−e)/(2×T)) − 25×h)
```

Nộp đúng trước hạn mới được điểm; tại đúng deadline hoặc sau deadline bị khóa nộp. Ví dụ màn weight 2 Easy: giải ngay 200 điểm, sau 90 giây 150 điểm, thêm 1 gợi ý còn 125 điểm. Điểm tối đa toàn bộ chuyến đi vẫn là 3.000/mode. Sai flag không có hình phạt riêng nhưng đồng hồ tiếp tục chạy.

**Hết giờ:** hiển thị 00:00, khóa nộp flag/gợi ý/tải artifact. Người chơi có thể chơi lại **bài hiện tại**: server cấp flag mới và đủ thời gian; giữ gợi ý đã mở và giảm điểm tính được còn 50% (làm tròn xuống), áp dụng cho mọi lượt sau lần đầu. Không có reset miễn phí trước hạn; các mảnh đã giải được giữ nguyên. Lượt đồng thời chỉ cấp lại một lần. Chuyến đi mới vẫn tạo phiên hoàn toàn mới như trước.

Bài đã giải dừng đồng hồ và giữ nguyên điểm; nộp lại không tăng điểm. BXH xếp số màn → tổng điểm (đã gồm thưởng tốc độ) → tổng thời gian hoàn thành chuyến đi. Tổng thời gian chuyến đi tính từ mở bài đầu đến giải bài cuối, kể cả thời gian chờ giữa bài. Các điểm đã lưu trước cập nhật không bị tính lại vì không có dữ liệu thời gian cũ; màn cũ được đánh dấu “luật cũ”, không dựng số giây giả.

Đồng hồ trình duyệt dùng mốc đơn điệu, đồng bộ server mỗi 10 giây và khi trở lại tab. Deadline và điểm được server kiểm tra trong giao dịch SQLite; thay giờ máy hoặc sửa request thời gian không thay đổi kết quả. Khi mất mạng đồng hồ vẫn chạy; bài chỉ được công nhận khi server nhận được đáp án đúng trước hạn.

Tên và điểm là dữ liệu công khai; tên có thể trùng, không phải tài khoản đã xác minh. Cookie giữ phiên 30 ngày. Đổi trình duyệt/xóa cookie mất quyền tiếp tục phiên cũ. “Chuyến đi mới” giữ hàng cũ trên BXH và tạo bộ flag mới.

## Logo chính thức đã cài

Hai ảnh người dùng cung cấp được lưu nguyên byte tại `assets/branding/originals/`:
- `club-primary-original.png`: bản chính, nền đen/chữ trắng.
- `club-alternative-original.jpg`: bản thay thế, nền trắng/chữ đen.

Bản dùng trên web là `public/club-logo.png` (PNG 1024×1024, thu nhỏ bản chính) và `public/club-logo-light.jpg` (bản JPEG thay thế nguyên gốc). Header và màn nhận thưởng dùng bản trắng ở giao diện sáng, bản đen ở giao diện tối. Giữ toàn bộ bố cục vuông, không cắt, không đảo màu, không tách nền; Next.js tự tối ưu kích thước tải về.

Theo cập nhật mới nhất: nền trang, panel và bản đồ trắng #FEFEFE ở theme sáng, đen #020202 ở theme tối để hòa với nền logo. Đảo và đường viền dùng xám trung tính; CTA giữ màu đất nung/cam đào để dễ nhận biết. Tiêu đề chính là “CMC Infrasec — Truy Tìm Kho Báu”. Kiểm tra contrast bằng `.\.venv\Scripts\python.exe scripts/check_palette.py`; kết quả chi tiết trong `evidence/footer-cleanup/palette-contrast.json`.

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

Footer hiện chỉ ghi `(c) CMC Infrasec x NextFest '26`. Logo chỉ có tại header/màn thưởng và không có viền. Nút chuyến đi mới ở cạnh tên/điểm guest. Nhãn Weight ≤ 10 đã bỏ khỏi giao diện; weight của bài chơi trong dữ liệu không thay đổi.

Toàn bộ giao diện dùng Poppins (400/500/600/700/800), tải font tại máy chủ ứng dụng, có glyph tiếng Việt; không gọi Google Fonts bên ngoài.

Bản Poppins Việt hóa (Vntype.Com & FontZin.Com) được tự host dưới dạng WOFF2 tại `public/fonts/`; SIL OFL và nguồn/commit/hash được giữ trong `assets/fonts/poppins-vietnamese/`. Các ký tự tiếng Việt được kiểm tra trực tiếp trong cmap font và bằng font thực tế mà trình duyệt render, không chỉ CSS font-family.
