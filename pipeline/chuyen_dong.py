"""Chế độ ảnh AI, bước chuyển động: biến ảnh tĩnh của mỗi shot thành chuỗi khung hình có camera chuyển động.

chuyen_dong (ghép được bằng dấu +, ví dụ "day_vao+lia_phai"):
    day_vao   camera đẩy vào          keo_ra    camera lùi ra
    lia_trai  lia sang trái            lia_phai  lia sang phải
    lia_len   lia lên                  lia_xuong lia xuống
    dung_yen  gần như đứng yên, trôi rất nhẹ
tieu_diem: [x, y] (0..1) điểm camera hướng vào, mặc định [0.5, 0.45].

Nếu cài được torch + transformers, pipeline ước lượng độ sâu ảnh (Depth Anything V2 Small) để làm parallax:
vật ở gần trôi nhanh hơn vật ở xa, tạo cảm giác 2.5D. Không có thì vẫn chạy, chỉ thiếu parallax.

    python pipeline/chuyen_dong.py build/gia_dinh_1788_anime/shots.json [--chi s01,s03]
"""
import hashlib
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chung import GOC, doc_json

Z_MAX = 1.16          # mức phóng lớn nhất
PARALLAX = 0.045      # độ mạnh parallax (tỉ lệ khung hình)
_MO_HINH_SAU = None


def _cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        sys.exit("Thiếu OpenCV: pip install opencv-python-headless")


def uoc_do_sau(anh_path, cache):
    """Bản đồ độ sâu 0..1 (1 = gần camera), lưu cache cạnh ảnh. None nếu không có torch/transformers."""
    global _MO_HINH_SAU
    cv2 = _cv2()
    if cache.exists() and cache.stat().st_mtime >= anh_path.stat().st_mtime:
        return cv2.imread(str(cache), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
    try:
        if _MO_HINH_SAU is None:
            from transformers import pipeline
            print("  Nạp model độ sâu Depth Anything V2 Small (lần đầu sẽ tải khoảng 100MB)...")
            _MO_HINH_SAU = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")
    except Exception as e:
        if _MO_HINH_SAU is None:
            print(f"  ! Không có parallax (cần pip install torch transformers): {str(e)[:120]}")
            _MO_HINH_SAU = False
        return None
    if _MO_HINH_SAU is False:
        return None
    from PIL import Image
    im = Image.open(anh_path).convert("RGB")
    d = np.asarray(_MO_HINH_SAU(im)["depth"].resize(im.size), dtype=np.float32)
    d = (d - d.min()) / max(1e-6, d.max() - d.min())
    d = cv2.GaussianBlur(d, (0, 0), 3)  # làm mềm mép để bớt xé hình
    cv2.imwrite(str(cache), (d * 255).astype(np.uint8))
    return d


def _em(u):
    """Easing: chậm đầu, chậm cuối."""
    return u * u * (3 - 2 * u)


def quy_dao(kieu, n):
    """Trả về danh sách (zoom, lệch_x, lệch_y, tiến_độ_parallax) cho n khung. Lệch tính theo tỉ lệ vùng lia được."""
    ds = []
    cac = set(kieu.split("+"))
    for i in range(n):
        u = _em(i / max(1, n - 1))
        z, ox, oy = 1.06, 0.0, 0.0
        if "day_vao" in cac:
            z = 1.0 + (Z_MAX - 1.0) * u
        elif "keo_ra" in cac:
            z = Z_MAX - (Z_MAX - 1.0) * u
        elif "dung_yen" in cac:
            z = 1.05 + 0.02 * u
        if cac & {"lia_trai", "lia_phai", "lia_len", "lia_xuong"} and not cac & {"day_vao", "keo_ra"}:
            z = 1.1
        if "lia_trai" in cac:
            ox = 0.45 - 0.9 * u
        if "lia_phai" in cac:
            ox = -0.45 + 0.9 * u
        if "lia_len" in cac:
            oy = 0.45 - 0.9 * u
        if "lia_xuong" in cac:
            oy = -0.45 + 0.9 * u
        if "dung_yen" in cac:
            ox = 0.04 * math.sin(u * math.pi)
        ds.append((z, ox, oy, u - 0.5))
    return ds


def cac_khung(anh_path, do_sau, s, W, H):
    """Sinh lần lượt từng khung (ảnh BGR W x H) của shot: camera chuyển động trên ảnh tĩnh + parallax."""
    cv2 = _cv2()
    src = cv2.imread(str(anh_path), cv2.IMREAD_COLOR)
    ih, iw = src.shape[:2]
    s0 = max(W / iw, H / ih)
    S = s0 * Z_MAX
    B = cv2.resize(src, (round(iw * S), round(ih * S)), interpolation=cv2.INTER_LANCZOS4)
    Bh, Bw = B.shape[:2]
    D = cv2.resize(do_sau, (Bw, Bh), interpolation=cv2.INTER_LINEAR) if do_sau is not None else None
    dm = float(np.median(D)) if D is not None else 0.0
    xs, ys = np.meshgrid(np.arange(W, dtype=np.float32) - W / 2, np.arange(H, dtype=np.float32) - H / 2)
    fx, fy = s.get("tieu_diem", [0.5, 0.45])
    kieu = s.get("chuyen_dong", "day_vao")
    cac = set(kieu.split("+"))
    for z, ox, oy, pu in quy_dao(kieu, s["so_frame"]):
        k = Z_MAX / z
        hw, hh = W / 2 * k, H / 2 * k
        # Tâm khung trong ảnh lớn: hướng về tiêu điểm, cộng phần lia, rồi kẹp để không lộ mép ảnh
        cx = np.clip(fx * Bw + ox * (Bw - 2 * hw), hw, Bw - hw)
        cy = np.clip(fy * Bh + oy * (Bh - 2 * hh), hh, Bh - hh)
        mx = (cx + xs * k).astype(np.float32)
        my = (cy + ys * k).astype(np.float32)
        if D is not None:
            d = cv2.remap(D, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) - dm
            p = PARALLAX * pu
            if cac & {"day_vao", "keo_ra", "dung_yen"}:  # vật gần phình ra / co lại nhanh hơn
                huong = 1 if "keo_ra" not in cac else -1
                mx = mx - xs * k * d * p * 2.2 * huong
                my = my - ys * k * d * p * 2.2 * huong
            if ox or oy:  # vật gần trôi ngang nhanh hơn khi lia
                mx = mx + d * p * W * k * np.sign(ox if ox else 0) * 1.5
                my = my + d * p * H * k * np.sign(oy if oy else 0) * 0.8
        yield cv2.remap(B, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REFLECT)


def lam_shot(anh_path, do_sau, s, W, H, out):
    cv2 = _cv2()
    for f in out.glob("f_*.png"):
        f.unlink()
    for i, fr in enumerate(cac_khung(anh_path, do_sau, s, W, H), 1):
        cv2.imwrite(str(out / f"f_{i:04d}.png"), fr, [cv2.IMWRITE_PNG_COMPRESSION, 1])


def tao(shots_json, chi=None):
    p = Path(shots_json)
    if not p.is_absolute():
        p = GOC / p
    data = doc_json(p)
    build = p.parent
    W, H = data["kho"]
    chieu_sau = data["anh_ai"].get("chieu_sau", True)
    print("Chuyển động 2.5D:")
    for s in data["shots"]:
        if chi and s["id"] not in chi:
            continue
        anh = build / "anh" / f"{s['id']}.png"
        if not anh.exists():
            sys.exit(f"Shot {s['id']} chưa có ảnh. Chạy bước tạo ảnh trước.")
        out = build / "khung" / s["id"]
        out.mkdir(parents=True, exist_ok=True)
        dau = hashlib.sha1(anh.read_bytes()).hexdigest()[:12] + s["hash"]
        h = out / ".hash"
        if h.exists() and h.read_text() == dau and len(list(out.glob("f_*.png"))) == s["so_frame"]:
            print(f"  [{s['id']}] không đổi, bỏ qua")
            continue
        do_sau = uoc_do_sau(anh, build / "anh" / f"{s['id']}_sau.png") if chieu_sau else None
        lam_shot(anh, do_sau, s, W, H, out)
        h.write_text(dau)
        print(f"  [{s['id']}] {s['so_frame']} khung, {s.get('chuyen_dong', 'day_vao')}"
              f"{', có parallax' if do_sau is not None else ''}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    chi = a[a.index("--chi") + 1].split(",") if "--chi" in a else None
    tao(next(x for x in a if x.endswith(".json")), chi)
