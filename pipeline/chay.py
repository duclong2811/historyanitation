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
import json
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
    on_twos = json.loads(Path(shots).read_text(encoding="utf-8")).get("on_twos", True)
    cmd = tim_blender() + [str(HERE / "render_blender.py"), "--", str(shots)]
    if xem_thu:
        cmd.append("--xem-thu")
    if may:
        cmd += ["--may", may]
    if chi:
        cmd += ["--chi", chi]
    # Lọc output của Blender: bỏ dòng rác (cảnh báo vô hại của Freestyle, từng dòng "Saved"),
    # chỉ hiện tiến độ và lỗi. Đặt biến môi trường HIEN_HET=1 để xem toàn bộ output gốc.
    if os.environ.get("HIEN_HET"):
        r = subprocess.run(cmd, cwd=GOC)
        if r.returncode:
            sys.exit("Render lỗi, xem thông báo ở trên.")
        return
    BO_QUA = ("appears twice", "EGL Error", "DeprecationWarning", "compositing_node_group",
              "use_nodes", "gpu.vulkan", "Blender quit", "Fra:", "Read prefs", "Blender 5", "Blender 4")
    p = subprocess.Popen(cmd, cwd=GOC, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    da_luu, tong, cuoi = 0, 0, []
    for dong in p.stdout:
        dong = dong.rstrip()
        cuoi = (cuoi + [dong])[-40:]
        if not dong or any(k in dong for k in BO_QUA):
            continue
        if "Saved:" in dong:
            da_luu += 1
            print(f"\r  đã render {da_luu}/{tong} khung", end="", flush=True)
            continue
        if dong.startswith("[s") and " render " in dong:  # "[s01] render 91 khung (...)"
            n = int(dong.split(" render ")[1].split()[0])
            tong = 1 if xem_thu else (n + 1) // 2 if on_twos else n
        if da_luu:
            print()
            da_luu = 0
        print(dong, flush=True)
    if da_luu:
        print()
    if p.wait():
        print("\n".join(cuoi))
        sys.exit("Render lỗi, xem 40 dòng cuối ở trên (chạy lại với HIEN_HET=1 để xem toàn bộ).")


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
