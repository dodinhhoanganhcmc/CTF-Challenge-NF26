"""Inert, session-specific beginner puzzles. No eval, shell, or vulnerable service."""
import base64
import hashlib
import hmac
import io
from PIL import Image, ImageDraw, PngImagePlugin

STAGES = [
    {"id": 1, "title": "Chai thư trôi dạt", "location": "Bãi Khởi Hành", "category": "Encoding", "weight": 2,
     "summary": "Một chai thư mắc trên bờ. Dòng ký tự bên trong đang chờ bạn đọc."},
    {"id": 2, "title": "La bàn xoay chữ", "location": "Rừng Xoay Chữ", "category": "Crypto", "weight": 4,
     "summary": "La bàn không chỉ hướng Bắc. Nó xoay cả những chữ cái trên đường đi."},
    {"id": 3, "title": "Bí mật đài quan sát", "location": "Đài Quan Sát", "category": "Web", "weight": 6,
     "summary": "Tấm bảng chỉ kể nửa câu chuyện. Phần còn lại nằm dưới bề mặt."},
    {"id": 4, "title": "Dấu vết ngọn hải đăng", "location": "Hải Đăng Ký Ức", "category": "Forensics", "weight": 8,
     "summary": "Người gác đèn để lại dữ liệu. Những mảnh rời vẫn nhớ thứ tự của chúng."},
    {"id": 5, "title": "Cánh cửa cuối cùng", "location": "Hang Kho Báu", "category": "Crypto + Misc", "weight": 10,
     "summary": "Dùng chìa khóa đã tìm thấy để đọc thông điệp sau lớp khóa cuối."},
]

WORDS = ["bottle", "compass", "observatory", "lighthouse", "treasure"]
KEYS = {"easy": "SAO", "hard": "LA_BAN"}


def flag_for(seed: str, mode: str, stage: int) -> str:
    suffix = hmac.new(bytes.fromhex(seed), f"{mode}:{stage}".encode(), hashlib.sha256).hexdigest()[:10]
    return f"DAO{{{WORDS[stage - 1]}_{suffix}}}"


def caesar(text: str, shift: int) -> str:
    return "".join(chr((ord(c) - base + shift) % 26 + base)
                   if (base := 65 if 'A' <= c <= 'Z' else 97 if 'a' <= c <= 'z' else 0) else c
                   for c in text)


def xor_bytes(text: str, key: str) -> bytes:
    k = key.encode()
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(text.encode()))


def puzzle(seed: str, mode: str, stage: int) -> dict:
    flag = flag_for(seed, mode, stage)
    easy = mode == "easy"
    shift = 3 if easy else 7
    encoded = base64.b64encode(flag.encode()).decode()
    if stage == 1:
        payload = encoded if easy else base64.b64encode(flag.encode().hex().encode()).decode()
        objective = "Giải Base64 để đọc lá thư và tìm flag." if easy else "Nhận diện các lớp biểu diễn của lá thư. Có nhiều hơn một lớp."
        hints = ["Base64 dùng A-Z, a-z, 0-9, dấu + và /; đôi khi kết thúc bằng =.",
                 "Chọn Base64 ở Bàn giải mã, dán nguyên lá thư rồi giải.",
                 "Kết quả phải bắt đầu bằng DAO{. Sao chép toàn bộ, kể cả dấu }." ] if easy else [
                     "Dấu = chỉ ra một lớp Base64.", "Kết quả đầu tiên chỉ có chữ số và a-f: đó là hex.", "Base64 → Hex → văn bản."]
        sample, tool = "SEVMTE8=", "base64"
    elif stage == 2:
        payload = caesar(flag, shift)
        objective = "Dịch lùi mỗi chữ cái 3 vị trí. Giữ nguyên số, dấu gạch dưới và dấu ngoặc." if easy else "La bàn có 26 nấc; chỉ chữ cái xoay. Tìm nấc làm hiện định dạng flag."
        hints = ["Caesar thay mỗi chữ bằng chữ ở cách nó một số vị trí.",
                 "D → A, E → B, F → C khi dịch lùi 3. Z nối lại với A.",
                 "Chọn Caesar, đặt nấc 3 rồi giải. Số và dấu ngoặc không đổi."] if easy else [
                     "Giữ nguyên dấu ngoặc và chữ số.", "Thử 26 phép dịch, tìm tiền tố DAO{.", "Thông điệp đã dịch tiến 7; cần dịch lùi 7."]
        sample, tool = "KHOOR", "caesar"
    elif stage == 3:
        payload = (f'<article>\n  <h1>Đài quan sát</h1>\n  <p>Nhìn kỹ hơn một chút.</p>\n'
                   f'  <!-- compass-fragment: {flag} -->\n</article>') if easy else (
                   f'<article data-cargo="{encoded}">\n  <h1>Đài quan sát</h1>\n'
                   '  <!-- DAO{not_the_real_cargo} là mồi nhử -->\n  <p>Hàng hóa nằm trong thuộc tính.</p>\n</article>')
        objective = "Đọc mã nguồn HTML. Bình luận không hiện trên trang, nhưng vẫn có trong mã nguồn." if easy else "Trang có một flag mồi nhử. Kiểm tra thuộc tính HTML và giải phần hàng hóa thực."
        hints = ["HTML là phần cấu trúc của một trang web.", "<!-- và --> bao quanh bình luận. Trình duyệt không hiển thị chúng.",
                 "Tìm dòng compass-fragment trong mã nguồn; flag ở ngay sau dấu hai chấm."] if easy else [
                     "Bình luận chứa mồi nhử, không phải đáp án.", "Thuộc tính data-cargo có thông điệp.", "Giải Base64 giá trị data-cargo."]
        sample, tool = '<p>Hello</p>\n<!-- note: look closer -->', "inspect"
    elif stage == 4:
        pieces = [flag[:8], flag[8:19], flag[19:]]
        payload = (f'09:12:03 INFO lamp=on\n09:12:06 FRAGMENT seq=3 text={pieces[2]}\n'
                   f'09:12:04 FRAGMENT seq=1 text={pieces[0]}\n09:12:05 FRAGMENT seq=2 text={pieces[1]}\n'
                   '09:12:07 INFO key_for_vault=SAO') if easy else (
                   'Ảnh hải đăng là tệp PNG. Người gác đèn lưu thông điệp trong metadata, không phải các pixel.\n'
                   'Khóa cho hang cuối: LA_BAN. Giữ nguyên chữ hoa và dấu gạch dưới.')
        objective = "Lọc dòng FRAGMENT rồi nối text theo seq 1, 2, 3. Không thêm khoảng trắng." if easy else "Tải ảnh gốc, kiểm tra trường Comment. Sắp xếp các mảnh rồi giải lớp hex."
        hints = ["Log là nhật ký sự kiện. Dòng INFO chỉ tạo bối cảnh.", "seq là số thứ tự; thứ tự các dòng đang bị đảo.",
                 "Ghép text của seq=1, rồi 2, rồi 3. Bàn giải mã có công cụ Ghép log."] if easy else [
                     "Tệp ảnh còn chứa metadata. Dùng exiftool hoặc trình đọc metadata.",
                     "Comment có các mảnh dạng số:hex; sắp theo số trước khi nối.",
                     "Nối hex của mảnh 1, 2, 3 rồi chuyển hex thành văn bản."]
        sample, tool = "FRAGMENT seq=2 text=LO\nFRAGMENT seq=1 text=HEL", "log"
    else:
        blob = xor_bytes(flag, KEYS[mode])
        payload = blob.hex() if easy else base64.b64encode(blob).decode()
        objective = "Giải XOR dạng hex bằng khóa SAO tìm được ở hải đăng." if easy else "Gỡ lớp biểu diễn trước, rồi XOR với khóa ở hải đăng. Lặp khóa đến hết dữ liệu."
        hints = ["XOR là phép toán byte. XOR hai lần với cùng khóa trả lại dữ liệu gốc.",
                 "Khóa SAO lặp lại: SAOSAOSAO… Chọn XOR (hex) ở Bàn giải mã.",
                 "Dán thông điệp, nhập SAO vào ô khóa. Kết quả đầy đủ là flag cuối."] if easy else [
                     "Bên ngoài là Base64, bên trong là byte đã XOR.",
                     "Khóa từ hải đăng: LA_BAN, phân biệt chữ hoa.", "Base64 ra bytes → XOR khóa lặp LA_BAN → UTF-8."]
        sample, tool = xor_bytes("HELLO", "SAO").hex(), "xor"
    return {"payload": payload, "objective": objective, "hints": hints,
            "sample": sample, "tool": tool, "artifact_name": "lighthouse.png" if stage == 4 and not easy else "clue.txt"}


def image_artifact(seed: str) -> bytes:
    flag = flag_for(seed, "hard", 4)
    hexed = flag.encode().hex()
    chunks = [hexed[:20], hexed[20:40], hexed[40:]]
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Title", "Hải Đăng Ký Ức")
    metadata.add_text("Comment", f"3:{chunks[2]}|1:{chunks[0]}|2:{chunks[1]}")
    metadata.add_text("VaultKey", KEYS["hard"])
    image = Image.new("RGB", (640, 360), (220, 239, 231))
    draw = ImageDraw.Draw(image)
    draw.rectangle((290, 80, 350, 300), fill=(243, 226, 197))
    draw.rectangle((280, 65, 360, 90), fill=(62, 91, 83))
    draw.rectangle((300, 95, 340, 125), fill=(230, 137, 85))
    draw.line((80, 305, 560, 305), fill=(62, 91, 83), width=3)
    out = io.BytesIO()
    image.save(out, format="PNG", pnginfo=metadata)
    return out.getvalue()


DEBRIEFS = [
    "Bạn vừa học encoding. Base64 và hex chỉ đổi cách biểu diễn; chúng không giữ bí mật như mã hóa có khóa.",
    "Bạn vừa giải Caesar. Khóa nhỏ chỉ có 26 khả năng; vì thế nó là bài học, không phải cách bảo vệ dữ liệu thật.",
    "Bạn vừa kiểm tra HTML. Dữ liệu gửi đến trình duyệt vẫn đọc được dù giao diện giấu nó đi.",
    "Bạn vừa phục hồi dấu vết. Thứ tự và metadata có thể giữ thông tin mà hình ảnh hoặc danh sách ban đầu không kể hết.",
    "Bạn vừa phối hợp biểu diễn byte và khóa XOR. Khóa lặp ngắn thích hợp cho bài học, không dùng để bảo vệ bí mật thật.",
]
