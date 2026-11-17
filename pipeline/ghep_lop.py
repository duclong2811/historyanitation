"""Chế độ lai, bước ghép lớp: nền (ảnh AI có camera chuyển động 2.5D) + nhân vật 3D (nền trong suốt).

Mỗi khung: lấy khung nền từ chuyen_dong.cac_khung, đặt khung nhân vật lên trên (nhân vật render on twos thì
mỗi khung nhân vật dùng cho 2 khung phim), pha nhẹ màu nhân vật theo tông màu của nền cho hòa hợp.
Ra: build/<tên>/khung/<shot>/f_####.png để ghep_phim.py ghép thành phim.

    python pipeline/ghep_lop.py build/<tên>/shots.json [--chi s01,s02]
"""
import hashlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chuyen_dong  # noqa: E402
from chung import GOC, doc_json  # noqa: E402

PHA_MAU = 0.28  # mức pha màu nhân vật theo nền (0 = giữ nguyên)


def _khung_nhan_vat(thu_muc):
    """số khung -> đường dẫn ảnh nhân vật"""
    ds = {}
    for p in thu_muc.glob("f_*.png"):
        try:
            ds[int(p.stem[2:])] = p
        except ValueError:
            pass
    return ds


def ghep_shot(s, build, W, H, chieu_sau, out):
    cv2 = chuyen_dong._cv2()
    nen = build / "anh" / f"{s['nen']}.png"
    if not nen.exists():
        sys.exit(f"Thiếu ảnh nền {nen.name}. Chạy bước tạo ảnh trước.")
    do_sau = chuyen_dong.uoc_do_sau(nen, build / "anh" / f"{s['nen']}_sau.png") if chieu_sau else None
    nv = _khung_nhan_vat(build / "nhan_vat" / s["id"]) if s.get("tren_hinh") else {}
    if s.get("tren_hinh") and not nv:
        sys.exit(f"Shot {s['id']} chưa render nhân vật. Chạy bước render nhân vật trước.")
    so_nv = sorted(nv)
    # Tông màu nền: nhân vật được nhuộm nhẹ theo tông này
    anh_nen = cv2.imread(str(nen), cv2.IMREAD_COLOR).astype(np.float32)
    tong = anh_nen.reshape(-1, 3).mean(0)
    nhuom = (1 - PHA_MAU) + PHA_MAU * tong / max(1.0, tong.mean())
    for f in out.glob("f_*.png"):
        f.unlink()
    cache = (None, None)
    for i, fr in enumerate(chuyen_dong.cac_khung(nen, do_sau, s, W, H), 1):
        if so_nv:
            k = max((x for x in so_nv if x <= i), default=so_nv[0])
            if cache[0] != k:
                lop = cv2.imread(str(nv[k]), cv2.IMREAD_UNCHANGED)
                if lop.shape[1] != W or lop.shape[0] != H:
                    lop = cv2.resize(lop, (W, H), interpolation=cv2.INTER_LANCZOS4)
                rgb = np.clip(lop[:, :, :3].astype(np.float32) * nhuom, 0, 255)
                a = lop[:, :, 3:4].astype(np.float32) / 255.0
                cache = (k, (rgb, a))
            rgb, a = cache[1]
            fr = (fr.astype(np.float32) * (1 - a) + rgb * a).astype(np.uint8)
        cv2.imwrite(str(out / f"f_{i:04d}.png"), fr, [cv2.IMWRITE_PNG_COMPRESSION, 1])


def xem_thu(shots_json, chi=None):
    """Mỗi shot một ảnh tĩnh: nền + ảnh nhân vật xem thử -> build/<tên>/xem_thu/sNN.png"""
    cv2 = chuyen_dong._cv2()
    p = Path(shots_json)
    if not p.is_absolute():
        p = GOC / p
    data = doc_json(p)
    build = p.parent
    W, H = (x * 40 // 100 for x in data["kho"])
    out = build / "xem_thu"
    out.mkdir(exist_ok=True)
    for s in data["shots"]:
        if chi and s["id"] not in chi:
            continue
        s1 = dict(s, so_frame=1, chuyen_dong="dung_yen")
        fr = next(chuyen_dong.cac_khung(build / "anh" / f"{s['nen']}.png", None, s1, W, H))
        lop_p = build / "nhan_vat" / "xem_thu" / f"{s['id']}.png"
        if s.get("tren_hinh") and lop_p.exists():
            lop = cv2.resize(cv2.imread(str(lop_p), cv2.IMREAD_UNCHANGED), (W, H))
            a = lop[:, :, 3:4].astype(np.float32) / 255.0
            fr = (fr * (1 - a) + lop[:, :, :3] * a).astype(np.uint8)
        cv2.imwrite(str(out / f"{s['id']}.png"), fr)


def tao(shots_json, chi=None):
    p = Path(shots_json)
    if not p.is_absolute():
        p = GOC / p
    data = doc_json(p)
    build = p.parent
    W, H = data["kho"]
    chieu_sau = data["anh_ai"].get("chieu_sau", True)
    print("Ghép lớp nền + nhân vật:")
    for s in data["shots"]:
        if chi and s["id"] not in chi:
            continue
        out = build / "khung" / s["id"]
        out.mkdir(parents=True, exist_ok=True)
        nen = build / "anh" / f"{s['nen']}.png"
        dau = (hashlib.sha1(nen.read_bytes()).hexdigest()[:12] if nen.exists() else "") + s["hash"]
        h = out / ".hash"
        if h.exists() and h.read_text() == dau and len(list(out.glob("f_*.png"))) == s["so_frame"]:
            print(f"  [{s['id']}] không đổi, bỏ qua")
            continue
        ghep_shot(s, build, W, H, chieu_sau, out)
        h.write_text(dau)
        ai = s["tren_hinh"][0] if s.get("tren_hinh") else "chỉ có nền"
        print(f"  [{s['id']}] {s['so_frame']} khung ({ai})")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    chi = a[a.index("--chi") + 1].split(",") if "--chi" in a else None
    tao(next(x for x in a if x.endswith(".json")), chi)
