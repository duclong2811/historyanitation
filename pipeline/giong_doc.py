"""Bước 3: giọng đọc, mỗi lời thoại một file build/<tên>/giong/sNN.wav.

  cach: piper   -> Piper TTS đọc offline, miễn phí. Tự tải giọng tiếng Việt nếu chưa có.
  cach: tu_thu  -> lấy file bạn tự thu: giong/<tên kịch bản>/s01.wav (hoặc .mp3/.m4a), s02...

    python pipeline/giong_doc.py kich-ban/mau.yaml
"""
import shutil
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chung import GOC, doc_kich_ban, ma_shot, thu_muc_build

KHO_GIONG = "https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN"
GIONG_SAN = {  # tên file -> đường dẫn trong kho giọng Piper
    "vi_VN-vais1000-medium.onnx": "vais1000/medium",
    "vi_VN-25hours_single-low.onnx": "25hours_single/low",
    "vi_VN-vivos-x_low.onnx": "vivos/x_low",
}


def tai_giong(mo_hinh: Path):
    if mo_hinh.exists() and Path(str(mo_hinh) + ".json").exists():
        return
    thu_muc = GIONG_SAN.get(mo_hinh.name)
    if not thu_muc:
        sys.exit(f"Không thấy giọng {mo_hinh}. Tải từ huggingface.co/rhasspy/piper-voices rồi đặt vào đó.")
    mo_hinh.parent.mkdir(parents=True, exist_ok=True)
    for ten in (mo_hinh.name, mo_hinh.name + ".json"):
        print(f"  Tải giọng {ten}...")
        urllib.request.urlretrieve(f"{KHO_GIONG}/{thu_muc}/{ten}", mo_hinh.parent / ten)


def doc_piper(kb, out):
    try:
        from piper import PiperVoice
    except ImportError:
        sys.exit("Chưa cài Piper: pip install piper-tts")
    cfg = kb.get("giong", {})
    mo_hinh = GOC / cfg.get("mo_hinh", "assets/giong/vi_VN-vais1000-medium.onnx")
    tai_giong(mo_hinh)
    voice = PiperVoice.load(str(mo_hinh))
    toc_do = float(cfg.get("toc_do", 1.0))
    for i, l in enumerate(kb["loi"], 1):
        dich = out / f"{ma_shot(i)}.wav"
        with wave.open(str(dich), "wb") as wf:
            try:  # piper-tts >= 1.3
                from piper import SynthesisConfig
                voice.synthesize_wav(l["noi"], wf, syn_config=SynthesisConfig(length_scale=toc_do))
            except ImportError:  # piper-tts 1.2
                voice.synthesize(l["noi"], wf, length_scale=toc_do)
        print(f"  {dich.name}: {l['noi'][:50]}")


def lay_tu_thu(kb, out):
    nguon = GOC / "giong" / kb["_ten"]
    thieu = []
    for i in range(1, len(kb["loi"]) + 1):
        sid = ma_shot(i)
        tep = next((p for p in nguon.glob(f"{sid}.*")), None)
        if not tep:
            thieu.append(sid)
            continue
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tep), "-ac", "1", "-ar", "44100",
                        str(out / f"{sid}.wav")], check=True)
    if thieu:
        sys.exit(f"Thiếu file thu âm trong {nguon.relative_to(GOC)}: {', '.join(thieu)}")


def tao(duong_dan_kb):
    kb = doc_kich_ban(duong_dan_kb)
    out = thu_muc_build(kb) / "giong"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    cach = kb.get("giong", {}).get("cach", "piper")
    print(f"Giọng đọc ({cach}):")
    if cach == "tu_thu":
        lay_tu_thu(kb, out)
    else:
        doc_piper(kb, out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    tao(sys.argv[1])
