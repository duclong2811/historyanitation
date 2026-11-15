"""Bước 2: chia kịch bản thành shot list (build/<tên>/shots.json).

Thời lượng mỗi shot lấy theo file giọng đọc nếu đã có, nếu chưa thì ước lượng theo số chữ.
    python pipeline/chia_shot.py kich-ban/mau.yaml
"""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chung import GOC, KHO, doc_kich_ban, ghi_json, ma_shot, thoi_luong_am_thanh, thu_muc_build

AM_TIET_MOI_GIAY = 4.5   # tốc độ nói tiếng Việt trung bình
DEM_CUOI = 0.35          # nghỉ sau mỗi câu (giây)
TOI_THIEU = 1.5          # shot ngắn nhất (giây)


def hash_tep(path):
    p = GOC / path
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12] if path and p.exists() else ""


def chia(duong_dan_kb):
    kb = doc_kich_ban(duong_dan_kb)
    out = thu_muc_build(kb)
    fps = int(kb.get("fps", 30))
    w, h = KHO.get(kb.get("kho_hinh", "doc"), KHO["doc"])

    shots, t = [], 0.0
    for i, l in enumerate(kb["loi"], 1):
        sid = ma_shot(i)
        giong = out / "giong" / f"{sid}.wav"
        dai_giong = thoi_luong_am_thanh(giong)
        if dai_giong is None:
            uoc = len(l["noi"].split()) / AM_TIET_MOI_GIAY
            dai = max(TOI_THIEU, uoc + DEM_CUOI)
        else:
            dai = max(TOI_THIEU, dai_giong + DEM_CUOI)
        so_frame = max(2, math.ceil(dai * fps))
        # Nhân vật có mặt: mọi nhân vật từng nói trong cảnh này
        co_mat = []
        for l2 in kb["loi"]:
            an = kb["nhan_vat"][l2["nhan_vat"]].get("an_hinh", False)  # người kể giấu mặt
            if l2["canh"] == l["canh"] and l2["nhan_vat"] not in co_mat and not an:
                co_mat.append(l2["nhan_vat"])
        canh = kb["canh"][l["canh"]]
        s = {
            "id": sid,
            "canh": l["canh"],
            "nhan_vat": l["nhan_vat"],
            "noi": l["noi"],
            "cam_xuc": l.get("cam_xuc", ""),
            "hanh_dong": l.get("hanh_dong", "dung_yen"),
            "camera": l.get("camera", "trung"),
            "co_mat": co_mat,
            "giong": str(giong.relative_to(GOC)) if dai_giong is not None else None,
            "bat_dau": round(t, 3),
            "thoi_luong": round(so_frame / fps, 3),
            "so_frame": so_frame,
        }
        # Hash: đổi bất cứ gì ảnh hưởng hình ảnh của shot thì shot đó được render lại
        y = {k: s[k] for k in ("canh", "nhan_vat", "hanh_dong", "camera", "co_mat", "so_frame")}
        y["canh_cfg"] = canh
        y["canh_tep"] = hash_tep(canh.get("dung", ""))
        y["nv"] = {n: kb["nhan_vat"][n] for n in co_mat}
        y["nv_tep"] = {n: hash_tep(kb["nhan_vat"][n].get("mo_hinh", "")) for n in co_mat}
        y["render"] = [w, h, kb.get("ty_le_render", 100), kb.get("on_twos", True)]
        y["code"] = [hash_tep("pipeline/render_blender.py"), hash_tep("pipeline/blender_tien_ich.py")]
        s["hash"] = hashlib.sha1(json.dumps(y, sort_keys=True).encode()).hexdigest()[:16]
        shots.append(s)
        t += so_frame / fps

    data = {
        "tieu_de": kb.get("tieu_de", kb["_ten"]),
        "ten": kb["_ten"],
        "kho": [w, h],
        "fps": fps,
        "on_twos": bool(kb.get("on_twos", True)),
        "ty_le_render": int(kb.get("ty_le_render", 100)),
        "phu_de": bool(kb.get("phu_de", True)),
        "nhac_nen": kb.get("nhac_nen", ""),
        "am_luong_nhac": float(kb.get("am_luong_nhac", 0.15)),
        "nhan_vat": kb["nhan_vat"],
        "canh": kb["canh"],
        "shots": shots,
    }
    ghi_json(out / "shots.json", data)
    print(f"Chia shot: {len(shots)} shot, tổng {t:.1f} giây -> {(out / 'shots.json').relative_to(GOC)}")
    return out / "shots.json"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    chia(sys.argv[1])
