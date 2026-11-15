"""Chạy cả pipeline: giọng đọc -> chia shot -> render Blender -> ghép phim.

    python pipeline/chay.py kich-ban/mau.yaml              # làm cả phim -> output/mau.mp4
    python pipeline/chay.py kich-ban/mau.yaml --xem-thu    # mỗi shot 1 ảnh nhỏ -> build/mau/xem_thu.png
    python pipeline/chay.py kich-ban/mau.yaml --bo-giong   # giữ giọng đã tạo, không đọc lại

Tùy chọn khác:
    --may cpu   render bằng CPU (Cycles) khi máy không có GPU
    --chi s01,s03  chỉ render các shot này (xem thử nhanh một vài shot)
Blender: đặt biến môi trường BLENDER=đường/dẫn/blender.exe nếu chương trình không tự tìm thấy.
"""
import glob
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from chung import GOC, doc_kich_ban, thu_muc_build  # noqa: E402


def tim_blender():
    if os.environ.get("BLENDER"):
        return [os.environ["BLENDER"], "-b", "--factory-startup", "-P"]
    b = shutil.which("blender")
    if not b:
        mau = [
            "C:/Program Files/Blender Foundation/Blender*/blender.exe",
            "C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe",
            os.path.expanduser("~/AppData/Local/Programs/Blender Foundation/Blender*/blender.exe"),
            "/Applications/Blender.app/Contents/MacOS/Blender",
        ]
        cac = [p for m in mau for p in sorted(glob.glob(m))]
        b = cac[-1] if cac else None
    if b:
        return [b, "-b", "--factory-startup", "-P"]
    if importlib.util.find_spec("bpy"):  # gói bpy cài bằng pip
        return [sys.executable]
    sys.exit("Không tìm thấy Blender. Cài Blender 4.2+ hoặc đặt biến BLENDER=đường/dẫn/blender.exe")


def render(shots, xem_thu, may, chi=None):
    cmd = tim_blender() + [str(HERE / "render_blender.py"), "--", str(shots)]
    if xem_thu:
        cmd.append("--xem-thu")
    if may:
        cmd += ["--may", may]
    if chi:
        cmd += ["--chi", chi]
    r = subprocess.run(cmd, cwd=GOC)
    if r.returncode:
        sys.exit("Render lỗi, xem thông báo ở trên.")


def to_xem_thu(build, so_shot):
    build = Path(build).resolve()
    anh = sorted((build / "xem_thu").glob("s*.png"))[:so_shot]
    try:
        from PIL import Image
    except ImportError:
        print(f"Ảnh xem thử nằm trong {(build / 'xem_thu').relative_to(GOC)}")
        return
    ims = [Image.open(a).convert("RGB") for a in anh]
    w, h = ims[0].size
    cot = min(len(ims), 4)
    hang = (len(ims) + cot - 1) // cot
    to = Image.new("RGB", (cot * w + (cot + 1) * 12, hang * h + (hang + 1) * 12), (30, 30, 30))
    for i, im in enumerate(ims):
        to.paste(im, (12 + (i % cot) * (w + 12), 12 + (i // cot) * (h + 12)))
    to.save(build / "xem_thu.png")
    print(f"Ảnh xem thử: {(build / 'xem_thu.png').relative_to(GOC)}")


def main():
    a = sys.argv[1:]
    kb_path = next((x for x in a if x.endswith((".yaml", ".yml"))), None)
    if not kb_path:
        sys.exit(__doc__)
    xem_thu, bo_giong = "--xem-thu" in a, "--bo-giong" in a
    may = a[a.index("--may") + 1] if "--may" in a else None
    chi = a[a.index("--chi") + 1] if "--chi" in a else None

    import chia_shot
    import ghep_phim
    import giong_doc

    kb = doc_kich_ban(kb_path)
    if not xem_thu and not bo_giong:
        giong_doc.tao(kb_path)
    shots = chia_shot.chia(kb_path)
    render(shots, xem_thu, may, chi)
    if xem_thu:
        to_xem_thu(thu_muc_build(kb), len(kb["loi"]))
    else:
        ghep_phim.ghep(shots)


if __name__ == "__main__":
    main()
