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


def _hash(y):
    return hashlib.sha1(json.dumps(y, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def shot_blender(kb, l, w, h):
    # Nhân vật có mặt: mọi nhân vật từng nói trong cảnh này
    co_mat = []
    for l2 in kb["loi"]:
        an = kb["nhan_vat"][l2["nhan_vat"]].get("an_hinh", False)  # người kể giấu mặt
        if l2["canh"] == l["canh"] and l2["nhan_vat"] not in co_mat and not an:
            co_mat.append(l2["nhan_vat"])
    canh = kb["canh"][l["canh"]]
    s = {"canh": l["canh"], "cam_xuc": l.get("cam_xuc", ""), "hanh_dong": l.get("hanh_dong", "dung_yen"),
         "camera": l.get("camera", "trung"), "co_mat": co_mat}
    y = {k: s[k] for k in ("canh", "hanh_dong", "camera", "co_mat")}
    y["nv_noi"] = l["nhan_vat"]
    y["canh_cfg"] = canh
    y["canh_tep"] = hash_tep(canh.get("dung", ""))
    y["nv"] = {n: kb["nhan_vat"][n] for n in co_mat}
    y["nv_tep"] = {n: hash_tep(kb["nhan_vat"][n].get("mo_hinh", "")) for n in co_mat}
    y["render"] = [w, h, kb.get("ty_le_render", 100), kb.get("on_twos", True), kb.get("net_vien", "freestyle")]
    y["code"] = [hash_tep("pipeline/render_blender.py"), hash_tep("pipeline/blender_tien_ich.py")]
    s["_y"] = y
    return s


def cau_hinh_anh(cfg, prompt, am, hat):
    return {"prompt": prompt, "am": am, "hat_giong": hat, "mo_hinh": cfg.get("mo_hinh", ""),
            "rong": cfg.get("rong", 832), "cao": cfg.get("cao", 1216), "buoc": cfg.get("buoc", 28),
            "cfg": cfg.get("cfg", 5.0), "sampler": cfg.get("sampler", "euler_ancestral"),
            "scheduler": cfg.get("scheduler", "normal"), "workflow": cfg.get("workflow", ""),
            "phong_to": cfg.get("phong_to", ""), "he_so_phong": cfg.get("he_so_phong", 2.0),
            "workflow_tep": hash_tep(cfg.get("workflow", ""))}


def _noi(*phan):
    return ", ".join(p.strip().strip(",") for p in phan if p and p.strip())


def nen_lai(kb):
    """Chế độ lai: mỗi cảnh một ảnh nền (không người), các shot cùng cảnh dùng chung."""
    cfg = kb.get("anh_ai", {})
    ds = {}
    for ten, c in kb["canh"].items():
        hat = c.get("hat_giong")
        if hat is None:
            hat = int(hashlib.sha1(f"{kb['_ten']}/nen/{ten}".encode()).hexdigest()[:8], 16)
        anh = cau_hinh_anh(cfg, _noi("no humans, scenery", c["ve"], cfg.get("phong_cach", "")),
                           _noi(c.get("am", ""), "1boy, 1girl, people, person", cfg.get("phong_cach_am", "")), hat)
        ds[f"nen_{ten}"] = {"anh": anh, "hash_anh": _hash(anh)}
    return ds


def shot_lai(kb, l, w, h, nen):
    """Chế độ lai: nền AI của cảnh + nhân vật VRoid render 3D đặt lên trên."""
    nv = kb["nhan_vat"]
    tren_hinh = l.get("tren_hinh")
    if tren_hinh is None:
        tren_hinh = [] if nv[l["nhan_vat"]].get("an_hinh") else [l["nhan_vat"]]
    for n in tren_hinh:
        if not str(nv[n].get("mo_hinh", "")).lower().endswith((".vrm", ".glb")):
            sys.exit(f"Chế độ lai: nhân vật '{n}' cần mo_hinh là file .vrm (VRoid) hoặc .glb")
    nid = f"nen_{l['canh']}"
    s = {"canh": l["canh"], "nen": nid, "tren_hinh": tren_hinh[:1],
         "dang_noi": l["nhan_vat"] in tren_hinh, "camera": l.get("camera", "trung"),
         "hanh_dong": l.get("hanh_dong", "dung_yen"), "cam_xuc": l.get("cam_xuc", ""),
         "vi_tri": l.get("vi_tri", 0.5), "goc_quay": l.get("goc_quay", 12),
         "chuyen_dong": l.get("chuyen_dong", "dung_yen"), "tieu_diem": l.get("tieu_diem", [0.5, 0.5])}
    s["_nv"] = {k: s[k] for k in ("tren_hinh", "dang_noi", "camera", "hanh_dong", "cam_xuc", "vi_tri", "goc_quay")}
    s["_nv"]["mo_hinh"] = [hash_tep(nv[n]["mo_hinh"]) for n in s["tren_hinh"]]
    s["_nv"]["cfg"] = {n: nv[n] for n in s["tren_hinh"]}  # đổi màu, phụ kiện... thì render lại
    s["_nv"]["dong_tac"] = hash_tep(f"assets/dong_tac/{s['hanh_dong']}.fbx")
    s["_nv"]["render"] = [w, h, kb.get("ty_le_render", 100), kb.get("on_twos", True)]
    s["_nv"]["code"] = [hash_tep("pipeline/render_nhan_vat.py"), hash_tep("pipeline/vrm.py")]
    s["_y"] = {"nen": nen[nid]["hash_anh"], "chuyen_dong": s["chuyen_dong"], "tieu_diem": s["tieu_diem"],
               "chieu_sau": kb.get("anh_ai", {}).get("chieu_sau", True), "kho": [w, h],
               "code": [hash_tep("pipeline/chuyen_dong.py"), hash_tep("pipeline/ghep_lop.py")]}
    return s


def shot_anh_ai(kb, l, sid, w, h):
    """Chế độ ảnh AI: ghép prompt = mô tả nhân vật có trên hình + mô tả riêng của shot + phong cách chung."""
    cfg = kb.get("anh_ai", {})
    nv = kb["nhan_vat"]
    tren_hinh = l.get("tren_hinh")
    if tren_hinh is None:
        tren_hinh = [] if nv[l["nhan_vat"]].get("an_hinh") else [l["nhan_vat"]]
    # Thứ tự theo cách model anime hiểu tốt nhất: nhân vật trước, rồi cảnh, cuối cùng là phong cách
    phan = [nv[n]["mo_ta"] for n in tren_hinh if nv[n].get("mo_ta")] + [l["ve"], cfg.get("phong_cach", "")]
    prompt = ", ".join(p.strip().strip(",") for p in phan if p and p.strip())
    am = ", ".join(p.strip().strip(",") for p in (l.get("am", ""), cfg.get("phong_cach_am", "")) if p and p.strip())
    hat = l.get("hat_giong")
    if hat is None:  # hạt giống cố định theo tên kịch bản + shot: chạy lại ra đúng ảnh cũ
        hat = int(hashlib.sha1(f"{kb['_ten']}/{sid}".encode()).hexdigest()[:8], 16)
    anh = cau_hinh_anh(cfg, prompt, am, hat)
    s = {"tren_hinh": tren_hinh, "chuyen_dong": l.get("chuyen_dong", "day_vao"),
         "tieu_diem": l.get("tieu_diem", [0.5, 0.45]), "anh": anh, "hash_anh": _hash(anh)}
    s["_y"] = {"hash_anh": s["hash_anh"], "chuyen_dong": s["chuyen_dong"], "tieu_diem": s["tieu_diem"],
               "chieu_sau": cfg.get("chieu_sau", True), "kho": [w, h],
               "code": hash_tep("pipeline/chuyen_dong.py")}
    return s


def chia(duong_dan_kb):
    kb = doc_kich_ban(duong_dan_kb)
    out = thu_muc_build(kb)
    fps = int(kb.get("fps", 30))
    w, h = KHO.get(kb.get("kho_hinh", "doc"), KHO["doc"])

    nen = nen_lai(kb) if kb.get("che_do") == "lai" else {}
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
        if kb.get("che_do") == "anh_ai":
            s = shot_anh_ai(kb, l, sid, w, h)
        elif kb.get("che_do") == "lai":
            s = shot_lai(kb, l, w, h, nen)
        else:
            s = shot_blender(kb, l, w, h)
        s.update({
            "id": sid,
            "nhan_vat": l["nhan_vat"],
            "noi": l["noi"],
            "giong": str(giong.relative_to(GOC)) if dai_giong is not None else None,
            "bat_dau": round(t, 3),
            "thoi_luong": round(so_frame / fps, 3),
            "so_frame": so_frame,
        })
        # Hash: đổi bất cứ gì ảnh hưởng hình ảnh của shot thì shot đó được làm lại
        if "_nv" in s:  # nhân vật nhép miệng theo giọng: đổi giọng thì render lại nhân vật
            s["hash_nv"] = _hash({"nv": s.pop("_nv"), "so_frame": so_frame, "giong": hash_tep(s["giong"] or "")})
            s["_y"]["hash_nv"] = s["hash_nv"]
        s["hash"] = _hash({"y": s.pop("_y"), "so_frame": so_frame})
        shots.append(s)
        t += so_frame / fps

    data = {
        "tieu_de": kb.get("tieu_de", kb["_ten"]),
        "ten": kb["_ten"],
        "kho": [w, h],
        "fps": fps,
        # Ảnh AI: chuyển động camera rẻ nên làm đủ 30 hình/giây cho mượt (chế độ lai: chỉ nhân vật on twos)
        "on_twos": bool(kb.get("on_twos", True)) and kb.get("che_do") != "anh_ai",
        "nen": nen,
        "ty_le_render": int(kb.get("ty_le_render", 100)),
        "phu_de": bool(kb.get("phu_de", True)),
        "net_vien": kb.get("net_vien", "freestyle"),
        "nhac_nen": kb.get("nhac_nen", ""),
        "am_luong_nhac": float(kb.get("am_luong_nhac", 0.15)),
        "che_do": kb.get("che_do", "blender"),
        "anh_ai": kb.get("anh_ai", {}),
        "nhan_vat": kb["nhan_vat"],
        "canh": kb.get("canh", {}),
        "shots": shots,
    }
    ghi_json(out / "shots.json", data)
    print(f"Chia shot: {len(shots)} shot, tổng {t:.1f} giây -> {(out / 'shots.json').relative_to(GOC)}")
    return out / "shots.json"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    chia(sys.argv[1])
