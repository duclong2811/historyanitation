"""Hàm dùng chung cho các bước của pipeline."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent  # thư mục gốc repo

KHO = {"doc": (1080, 1920), "ngang": (1920, 1080)}


def doc_kich_ban(duong_dan):
    import yaml
    p = Path(duong_dan)
    kb = yaml.safe_load(p.read_text(encoding="utf-8"))
    kb["_ten"] = p.stem
    anh_ai = kb.get("che_do") == "anh_ai"
    for k in ("nhan_vat", "loi") if anh_ai else ("nhan_vat", "canh", "loi"):
        if not kb.get(k):
            sys.exit(f"Kịch bản thiếu mục '{k}'.")
    if kb.get("che_do") == "lai":
        for ten, c in kb["canh"].items():
            if not c.get("ve"):
                sys.exit(f"Chế độ lai: cảnh '{ten}' thiếu 've' (prompt vẽ ảnh nền).")
    for i, l in enumerate(kb["loi"], 1):
        for k in ("nhan_vat", "noi", "ve") if anh_ai else ("canh", "nhan_vat", "noi"):
            if not l.get(k):
                sys.exit(f"Lời thứ {i} thiếu '{k}'.")
        if not anh_ai and l["canh"] not in kb["canh"]:
            sys.exit(f"Lời thứ {i}: cảnh '{l['canh']}' chưa khai báo trong mục canh.")
        if l["nhan_vat"] not in kb["nhan_vat"]:
            sys.exit(f"Lời thứ {i}: nhân vật '{l['nhan_vat']}' chưa khai báo trong mục nhan_vat.")
    return kb


def thu_muc_build(kb):
    d = GOC / "build" / kb["_ten"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def ma_shot(i):
    return f"s{i:02d}"


def thoi_luong_am_thanh(path):
    """Độ dài file âm thanh (giây), None nếu không đọc được."""
    if not shutil.which("ffprobe") or not Path(path).exists():
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def ghi_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def doc_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
