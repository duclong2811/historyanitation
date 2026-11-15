"""Bước 5: render từng shot bằng Blender.

Chạy trong Blender (chay.py tự gọi giúp):
    blender -b --factory-startup -P pipeline/render_blender.py -- build/mau/shots.json [--xem-thu] [--may cpu]
Hoặc với gói bpy cài bằng pip:
    python pipeline/render_blender.py build/mau/shots.json

--xem-thu : mỗi shot render 1 ảnh nhỏ ở giữa shot -> build/<tên>/xem_thu/
--may cpu : dùng Cycles trên CPU (máy không có GPU). Mặc định là Eevee (nhanh, cần GPU).
Shot nào không đổi so với lần render trước thì bỏ qua.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
GOC = HERE.parent
sys.path.insert(0, str(HERE))
import blender_tien_ich as t  # noqa: E402

CAO_NHAN_VAT = 1.7

# Khung hình theo cỡ cảnh: (khoảng cách, chiều cao camera, tiêu cự, chiều cao điểm nhìn)
CAMERA = {
    "rong": (6.5, 1.9, 32, 1.0),
    "trung": (3.6, 1.5, 40, 1.15),
    "can": (2.4, 1.5, 55, 1.4),
}

# Ánh sáng theo giờ: (màu trời, màu nắng, cường độ nắng, độ cao mặt trời °, hướng °)
GIO = {
    "sang": ("#cfe3f0", "#fff1d6", 3.0, 25, -40),
    "trua": ("#bcd9f2", "#ffffff", 4.0, 70, -20),
    "chieu": ("#f2d2a8", "#ffc48a", 3.0, 18, 35),
    "dem": ("#1d2540", "#9fb4ff", 0.6, 45, 20),
}


def doi_so():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ch = {"shots": None, "xem_thu": "--xem-thu" in a, "may": "gpu"}
    for i, x in enumerate(a):
        if x == "--may" and i + 1 < len(a):
            ch["may"] = a[i + 1]
        elif x.endswith(".json"):
            ch["shots"] = x
    if not ch["shots"]:
        sys.exit(__doc__)
    return ch


def engine_eevee():
    co = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    return "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in co else "BLENDER_EEVEE"


def lam_moi(data, ch):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t._VAT_LIEU.clear()
    sc = bpy.context.scene
    r = sc.render
    w, h = data["kho"]
    r.resolution_x, r.resolution_y = w, h
    r.resolution_percentage = 40 if ch["xem_thu"] else data["ty_le_render"]
    r.fps = data["fps"]
    r.image_settings.file_format = "PNG"
    r.film_transparent = False
    if ch["may"] == "cpu":
        t.ENGINE = "CYCLES"
        r.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = 8 if ch["xem_thu"] else 24
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 3
    else:
        t.ENGINE = "EEVEE"
        r.engine = engine_eevee()
        sc.eevee.taa_render_samples = 8 if ch["xem_thu"] else 16
    # Nét viền kiểu tranh vẽ
    r.use_freestyle = True
    r.line_thickness_mode = "RELATIVE"
    fs = bpy.context.view_layer.freestyle_settings
    lset = fs.linesets[0] if fs.linesets else fs.linesets.new("net_vien")
    if lset.linestyle is None:
        lset.linestyle = bpy.data.linestyles.new("net_vien")
    lset.linestyle.color = (0.08, 0.06, 0.05)
    lset.linestyle.thickness = 1.6
    sc.view_settings.view_transform = "Standard"
    return sc


def anh_sang(gio):
    troi, nang, manh, cao, huong = GIO.get(gio, GIO["chieu"])
    w = bpy.data.worlds.new("troi")
    if bpy.app.version < (5, 0, 0):  # từ Blender 5 world luôn dùng node
        w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = t.mau_rgb(troi)
    bg.inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = w
    l = bpy.data.lights.new("mat_troi", "SUN")
    l.color = t.mau_rgb(nang)[:3]
    l.energy = manh
    l.angle = math.radians(3)
    ob = bpy.data.objects.new("mat_troi", l)
    ob.rotation_euler = (math.radians(90 - cao), 0, math.radians(huong))
    bpy.context.scene.collection.objects.link(ob)


def dung_canh(cfg):
    p = GOC / cfg["dung"]
    spec = importlib.util.spec_from_file_location(f"canh_{p.stem}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.dung(t)


# ---------- Nhân vật ----------

def hinh_nom(ten, mau):
    """Hình nộm tạm khi chưa có mô hình: thân, đầu, mắt, hai tay."""
    than = t.tru(f"{ten}_than", 0.32, 0.22, 1.05, (0, 0, 0), mau)
    than.location.z = 0.0
    dau = t.cau(f"{ten}_dau", 0.27, (0, 0, 1.33), "#f1d3b3", cha=than)
    dau["vai_tro"] = "dau"
    for s in (-1, 1):
        t.cau(f"{ten}_mat{s}", 0.035, (0.09 * s, -0.24, 0.04), "#1a1410", cha=dau)
    t.khoi(f"{ten}_toc", (0.5, 0.5, 0.14), (0, 0.03, 0.17), "#2b1d14", cha=dau)
    tay = {}
    for s, phia in ((-1, "trai"), (1, "phai")):
        a = t.tru(f"{ten}_tay_{phia}", 0.07, 0.06, 0.62, (0.33 * s, 0, 0.98), mau, dich_z=-0.5, cha=than)
        tay[phia] = a
    return {"goc": than, "dau": dau, "tay": tay, "nom": True}


def nap_mo_hinh(ten, path):
    p = GOC / path
    truoc = set(bpy.data.objects)
    duoi = p.suffix.lower()
    if duoi in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(p))
    elif duoi == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(p))
    elif duoi == ".vrm":
        if not hasattr(bpy.ops.import_scene, "vrm"):
            raise RuntimeError("cần cài VRM Add-on for Blender, hoặc xuất VRoid sang .glb")
        bpy.ops.import_scene.vrm(filepath=str(p))
    else:
        raise RuntimeError(f"không hỗ trợ đuôi {duoi}")
    moi = [o for o in bpy.data.objects if o not in truoc]
    goc = bpy.data.objects.new(f"{ten}_goc", None)
    bpy.context.scene.collection.objects.link(goc)
    for o in moi:
        if o.parent is None:
            o.parent = goc
    # Chuẩn hóa chiều cao về CAO_NHAN_VAT, chân chạm đất
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in moi if o.type == "MESH" for c in o.bound_box]
    if zs:
        k = CAO_NHAN_VAT / max(1e-3, max(zs) - min(zs))
        goc.scale = (k, k, k)
        goc.location.z = -min(zs) * k
    khung = next((o for o in moi if o.type == "ARMATURE"), None)
    return {"goc": goc, "khung": khung, "nom": False}


def gan_dong_tac(nv, hanh_dong):
    """Gắn động tác Mixamo (assets/dong_tac/<tên>.fbx) cho mô hình có khung xương cùng tên xương."""
    p = GOC / "assets" / "dong_tac" / f"{hanh_dong}.fbx"
    if not nv.get("khung") or not p.exists():
        return False
    truoc_ob, truoc_act = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=str(p))
    act = next((a for a in bpy.data.actions if a not in truoc_act), None)
    for o in set(bpy.data.objects) - truoc_ob:
        bpy.data.objects.remove(o, do_unlink=True)
    if not act:
        return False
    ad = nv["khung"].animation_data or nv["khung"].animation_data_create()
    ad.action = act
    if getattr(act, "slots", None) and hasattr(ad, "action_slot"):
        ad.action_slot = act.slots[0]
    return True


def key(ob, prop, f, gia_tri, chi_so):
    getattr(ob, prop)[chi_so] = gia_tri
    ob.keyframe_insert(prop, index=chi_so, frame=f)


def hoat_hinh_nom(nv, shot, dang_noi, fps):
    """Chuyển động đơn giản cho hình nộm: thở, nhép đầu khi nói, vẫy / chỉ tay, gật đầu."""
    n = shot["so_frame"]
    than, dau, tay = nv["goc"], nv["dau"], nv["tay"]
    for f in range(1, n + 1, 4):
        key(than, "scale", f, 1 + 0.012 * math.sin(f / fps * 2.5), 2)
    if not dang_noi:
        return
    for f in range(1, n + 1, 3):  # đầu nhún nhẹ theo nhịp nói
        key(dau, "scale", f, 1 + 0.035 * abs(math.sin(f / fps * 9)), 2)
    hd = shot["hanh_dong"]
    p = tay["phai"]
    if hd == "vay_tay":
        for f in range(1, n + 1, 3):
            key(p, "rotation_euler", f, -2.6 + 0.35 * math.sin(f / fps * 8), 1)
    elif hd == "chi_tay":
        key(p, "rotation_euler", 1, 0, 1)
        key(p, "rotation_euler", min(n, 8), -1.45, 1)
        key(p, "rotation_euler", min(n, 8), -0.5, 2)
        key(p, "rotation_euler", 1, 0, 2)
    elif hd == "gat_dau":
        for f in range(1, n + 1, 3):
            key(dau, "rotation_euler", f, 0.22 * max(0, math.sin(f / fps * 7)), 0)


def dat_nhan_vat(data, shot):
    ds = shot["co_mat"]
    vt = {}
    for i, ten in enumerate(ds):
        cfg = data["nhan_vat"][ten]
        x = (i - (len(ds) - 1) / 2) * 1.3
        nv = None
        if cfg.get("mo_hinh"):
            try:
                nv = nap_mo_hinh(ten, cfg["mo_hinh"])
            except Exception as e:  # mô hình hỏng thì dùng hình nộm, không dừng cả phim
                print(f"  ! {ten}: không nạp được mô hình ({e}), dùng hình nộm")
        if nv is None:
            nv = hinh_nom(ten, cfg.get("mau", "#888888"))
        nv["goc"].location.x = x
        # Quay nhẹ vào giữa như đang trò chuyện
        nv["goc"].rotation_euler.z = -0.25 * (x / 1.3) if len(ds) > 1 else 0
        dang_noi = ten == shot["nhan_vat"]
        if nv["nom"]:
            hoat_hinh_nom(nv, shot, dang_noi, data["fps"])
        elif dang_noi:
            gan_dong_tac(nv, shot["hanh_dong"])
        vt[ten] = x
    return vt


def dat_camera(data, shot, vt):
    dist, cao, tieu_cu, nhin_z = CAMERA.get(shot["camera"], CAMERA["trung"])
    if shot["camera"] == "rong" or shot["nhan_vat"] not in vt:
        tx = sum(vt.values()) / max(1, len(vt))
    else:
        tx = vt[shot["nhan_vat"]]
    if data["kho"][0] > data["kho"][1]:  # khổ ngang: lùi thêm cho đủ người
        dist *= 0.85
    dich = Vector((tx, 0, nhin_z))
    muc = bpy.data.objects.new("diem_nhin", None)
    muc.location = dich
    bpy.context.scene.collection.objects.link(muc)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = tieu_cu
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.scene.collection.objects.link(cam)
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = muc, "TRACK_NEGATIVE_Z", "UP_Y"
    # Đẩy camera vào thật chậm trong suốt shot
    n = shot["so_frame"]
    for f, k in ((1, 1.07), (n, 1.0)):
        cam.location = (tx + 0.15 * dist, -dist * k, cao)
        cam.keyframe_insert("location", frame=f)
    bpy.context.scene.camera = cam


def render_shot(data, shot, ch, build):
    sc = lam_moi(data, ch)
    cfg = data["canh"][shot["canh"]]
    anh_sang(cfg.get("gio", "chieu"))
    dung_canh(cfg)
    vt = dat_nhan_vat(data, shot)
    dat_camera(data, shot, vt)
    sc.frame_start, sc.frame_end = 1, shot["so_frame"]
    if ch["xem_thu"]:
        out = build / "xem_thu"
        out.mkdir(exist_ok=True)
        sc.frame_set(max(1, shot["so_frame"] // 2))
        sc.render.filepath = str(out / f"{shot['id']}.png")
        bpy.ops.render.render(write_still=True)
        return
    out = build / "khung" / shot["id"]
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    sc.frame_step = 2 if data["on_twos"] else 1
    sc.render.filepath = str(out / "f_")
    bpy.ops.render.render(animation=True)
    (out / ".hash").write_text(shot["hash"])


def main():
    ch = doi_so()
    path = Path(ch["shots"])
    if not path.is_absolute():
        path = GOC / path
    data = json.loads(path.read_text(encoding="utf-8"))
    build = path.parent
    for shot in data["shots"]:
        h = build / "khung" / shot["id"] / ".hash"
        if not ch["xem_thu"] and h.exists() and h.read_text() == shot["hash"]:
            print(f"[{shot['id']}] không đổi, bỏ qua")
            continue
        print(f"[{shot['id']}] render {shot['so_frame']} khung ({shot['camera']}, {shot['nhan_vat']})")
        render_shot(data, shot, ch, build)


if __name__ == "__main__":
    main()
