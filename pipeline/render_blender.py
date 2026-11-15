"""Bước 5: render từng shot bằng Blender.

Chạy trong Blender (chay.py tự gọi giúp):
    blender -b --factory-startup -P pipeline/render_blender.py -- build/mau/shots.json [--xem-thu] [--may cpu]
Hoặc với gói bpy cài bằng pip:
    python pipeline/render_blender.py build/mau/shots.json

--xem-thu : mỗi shot render 1 ảnh nhỏ ở giữa shot -> build/<tên>/xem_thu/
--may cpu : dùng Cycles trên CPU (máy không có GPU). Mặc định là Eevee (nhanh, cần GPU).
Shot nào không đổi so với lần render trước thì bỏ qua.

Script cảnh (canh/*.py) có hàm dung(t) và có thể trả về:
    {"cho_dung": {"<nhân vật>": {"vi_tri": (x, y, z), "huong": độ, "cha": "<tên object>"}},
     "camera":   {"<tên>": {"vi_tri": (x, y, z), "nhin": (x, y, z), "tieu_cu": 35, "day": (dx, dy, dz)}}}
Trong kịch bản, camera của shot là rong | trung | can (theo người nói) hoặc tên một camera của cảnh.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
GOC = HERE.parent
sys.path.insert(0, str(HERE))
import blender_tien_ich as t  # noqa: E402

CAO_NHAN_VAT = 1.7

# Khung hình theo người nói: (khoảng cách, độ cao camera so với chân, tiêu cự, độ cao điểm nhìn)
CAMERA = {
    "rong": (6.5, 1.9, 32, 1.0),
    "trung": (3.4, 1.55, 40, 1.25),
    "can": (2.2, 1.6, 55, 1.55),
}

# Ánh sáng mặc định theo giờ: (màu trời, màu nắng, cường độ nắng, độ cao mặt trời °, hướng °)
GIO = {
    "sang": ("#cfe3f0", "#fff1d6", 3.0, 25, -40),
    "trua": ("#bcd9f2", "#ffffff", 4.0, 70, -20),
    "chieu": ("#f2d2a8", "#ffc48a", 3.0, 18, 35),
    "dem": ("#1d2540", "#9fb4ff", 0.6, 45, 20),
}


def doi_so():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ch = {"shots": None, "xem_thu": "--xem-thu" in a, "may": "gpu", "chi": None}
    for i, x in enumerate(a):
        if x == "--may" and i + 1 < len(a):
            ch["may"] = a[i + 1]
        elif x == "--chi" and i + 1 < len(a):  # chỉ render các shot này, ví dụ --chi s01,s03
            ch["chi"] = a[i + 1].split(",")
        elif x.endswith(".json"):
            ch["shots"] = x
    if not ch["shots"]:
        sys.exit(__doc__)
    return ch


def engine_eevee():
    co = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    return "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in co else "BLENDER_EEVEE"


def lam_moi(data, shot, ch):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t._VAT_LIEU.clear()
    t.SO_FRAME, t.FPS = shot["so_frame"], data["fps"]
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
        sc.eevee.taa_render_samples = 16 if ch["xem_thu"] else 24
        for k, v in (("volumetric_tile_size", "8"), ("volumetric_end", 250.0), ("use_shadows", True)):
            if hasattr(sc.eevee, k):
                setattr(sc.eevee, k, v)
    # Nét viền kiểu tranh vẽ
    r.use_freestyle = True
    r.line_thickness_mode = "RELATIVE"
    fs = bpy.context.view_layer.freestyle_settings
    lset = fs.linesets[0] if fs.linesets else fs.linesets.new("net_vien")
    if lset.linestyle is None:
        lset.linestyle = bpy.data.linestyles.new("net_vien")
    lset.linestyle.color = (0.10, 0.07, 0.05)
    lset.linestyle.thickness = 1.3
    lset.select_by_visibility = True
    lset.select_crease = False  # bỏ nét ở nếp gấp nhỏ, chỉ giữ đường bao và cạnh sắc
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    hau_ky(sc)
    return sc


def hau_ky(sc):
    """Compositor: glare (vầng sáng quanh chỗ sáng) cho ánh nắng mềm hơn."""
    try:
        if hasattr(sc, "compositing_node_group"):  # Blender 5
            ng = bpy.data.node_groups.new("hau_ky", "CompositorNodeTree")
            ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            out = ng.nodes.new("NodeGroupOutput")
            sc.compositing_node_group = ng
        else:  # Blender 4.x
            sc.use_nodes = True
            ng = sc.node_tree
            ng.nodes.clear()
            out = ng.nodes.new("CompositorNodeComposite")
        rl = ng.nodes.new("CompositorNodeRLayers")
        gl = ng.nodes.new("CompositorNodeGlare")
        cai = {"glare_type": "FOG_GLOW", "quality": "MEDIUM", "threshold": 0.85, "size": 7, "mix": -0.75}
        for k, v in cai.items():
            if hasattr(gl, k):
                try:
                    setattr(gl, k, v)
                except Exception:
                    pass
        for ten, v in (("Type", "Fog Glow"), ("Threshold", 0.85), ("Strength", 0.35), ("Size", 0.6)):
            s = gl.inputs.get(ten)
            if s is not None and hasattr(s, "default_value"):
                try:
                    s.default_value = v
                except Exception:
                    pass
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs["Image"], out.inputs[0])
    except Exception as e:
        print(f"  ! Bỏ qua hậu kỳ: {e}")


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
    return mod.dung(t) or {}


# ---------- Nhân vật ----------

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
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in moi if o.type == "MESH" for c in o.bound_box]
    if zs:
        k = CAO_NHAN_VAT / max(1e-3, max(zs) - min(zs))
        for o in moi:
            if o.parent is goc:
                o.location *= k
                o.scale *= k
                o.location.z -= min(zs) * k
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
    """Chuyển động cho hình nộm: thở, nhún đầu khi nói, vẫy / chỉ tay / giơ cao, gật đầu."""
    n = shot["so_frame"]
    than, dau, tay = nv["than"], nv["dau"], nv["tay"]
    for f in range(1, n + 2, 4):
        key(than, "scale", f, 1 + 0.01 * math.sin(f / fps * 2.5), 2)
    if not dang_noi:
        return
    for f in range(1, n + 2, 3):  # đầu nhún nhẹ theo nhịp nói
        key(dau, "rotation_euler", f, 0.05 * math.sin(f / fps * 9), 0)
    hd = shot["hanh_dong"]
    p = tay["phai"]
    if hd == "vay_tay":
        for f in range(1, n + 2, 3):
            key(p, "rotation_euler", f, -2.6 + 0.35 * math.sin(f / fps * 8), 1)
    elif hd == "chi_tay":
        key(p, "rotation_euler", 1, 0, 0)
        key(p, "rotation_euler", min(n, 8), -1.45, 0)
        key(p, "rotation_euler", min(n, 8), -0.3, 1)
        key(p, "rotation_euler", 1, 0, 1)
    elif hd == "gio_cao":  # giơ cao tay (ra lệnh, hô quân)
        key(p, "rotation_euler", 1, 0, 1)
        key(p, "rotation_euler", min(n, 7), -2.9, 1)
        for f in range(8, n + 2, 4):
            key(p, "rotation_euler", f, -2.9 + 0.12 * math.sin(f / fps * 6), 1)
    elif hd == "gat_dau":
        for f in range(1, n + 2, 3):
            key(dau, "rotation_euler", f, 0.22 * max(0, math.sin(f / fps * 7)), 0)


def dat_nhan_vat(data, shot, info):
    ds = shot["co_mat"]
    cho = info.get("cho_dung", {})
    ket = {}
    for i, ten in enumerate(ds):
        cfg = data["nhan_vat"][ten]
        c = cho.get(ten, {})
        vt = c.get("vi_tri", ((i - (len(ds) - 1) / 2) * 1.3, 0, 0))
        huong = math.radians(c.get("huong", 0))
        nv = None
        if cfg.get("mo_hinh"):
            try:
                nv = nap_mo_hinh(ten, cfg["mo_hinh"])
            except Exception as e:  # mô hình hỏng thì dùng hình nộm, không dừng cả phim
                print(f"  ! {ten}: không nạp được mô hình ({e}), dùng hình nộm")
        if nv is None:
            nv = t.nguoi(ten, mau_ao=cfg.get("mau", "#888888"), mau_quan=cfg.get("mau_quan", "#2a2420"),
                         dau=cfg.get("dau", "khan_van"), mau_khan=cfg.get("mau_khan", "#2b2420"),
                         cam=cfg.get("cam", ""))
        g = nv["goc"]
        g.location, g.rotation_euler.z = vt, huong
        if c.get("cha") and bpy.data.objects.get(c["cha"]):
            cha = bpy.data.objects[c["cha"]]
            bpy.context.view_layer.update()
            g.parent = cha
            g.matrix_parent_inverse = cha.matrix_world.inverted()
        dang_noi = ten == shot["nhan_vat"]
        if nv["nom"]:
            hoat_hinh_nom(nv, shot, dang_noi, data["fps"])
        elif dang_noi:
            gan_dong_tac(nv, shot["hanh_dong"])
        ket[ten] = g
    bpy.context.view_layer.update()
    return ket


def tao_camera(vi_tri_dau, vi_tri_cuoi, nhin, tieu_cu):
    sc = bpy.context.scene
    muc = bpy.data.objects.new("diem_nhin", None)
    muc.location = nhin
    sc.collection.objects.link(muc)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = tieu_cu
    cam_d.clip_end = 1000
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = muc, "TRACK_NEGATIVE_Z", "UP_Y"
    for f, p in ((1, vi_tri_dau), (t.SO_FRAME, vi_tri_cuoi)):  # đẩy camera thật chậm trong suốt shot
        cam.location = p
        cam.keyframe_insert("location", frame=f)
    sc.camera = cam


def dat_camera(data, shot, info, nv):
    cams = info.get("camera", {})
    ten_cam = shot["camera"]
    if ten_cam not in CAMERA and ten_cam not in cams:
        ten_cam = "rong"
    if ten_cam in cams:
        c = cams[ten_cam]
        p = Vector(c["vi_tri"])
        day = Vector(c.get("day", (0, 0, 0)))
        tao_camera(p, p + day, c["nhin"], c.get("tieu_cu", 35))
        return
    noi = nv.get(shot["nhan_vat"])
    if noi is None:  # người kể không hiện hình: dùng camera đầu tiên của cảnh
        if cams:
            c = next(iter(cams.values()))
            p = Vector(c["vi_tri"])
            tao_camera(p, p + Vector(c.get("day", (0, 0, 0))), c["nhin"], c.get("tieu_cu", 35))
        else:
            tao_camera(Vector((1, -9, 2)), Vector((1, -8.4, 2)), (0, 0, 1), 32)
        return
    dist, cao, tieu_cu, nhin_z = CAMERA[ten_cam]
    if data["kho"][0] > data["kho"][1]:
        dist *= 0.85
    goc = noi.matrix_world.translation
    yaw = noi.matrix_world.to_euler().z
    if ten_cam == "rong" and len(nv) > 1:
        goc = sum((o.matrix_world.translation for o in nv.values()), Vector()) / len(nv)
    lech = Matrix.Rotation(yaw, 3, "Z") @ Vector((0.15 * dist, -dist, 0))
    nhin = goc + Vector((0, 0, nhin_z))
    p_cuoi = goc + lech + Vector((0, 0, cao))
    p_dau = goc + lech * 1.07 + Vector((0, 0, cao))
    tao_camera(p_dau, p_cuoi, nhin, tieu_cu)


def render_shot(data, shot, ch, build):
    sc = lam_moi(data, shot, ch)
    cfg = data["canh"][shot["canh"]]
    anh_sang(cfg.get("gio", "chieu"))
    info = dung_canh(cfg)
    nv = dat_nhan_vat(data, shot, info)
    dat_camera(data, shot, info, nv)
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
        if ch["chi"] and shot["id"] not in ch["chi"]:
            continue
        h = build / "khung" / shot["id"] / ".hash"
        if not ch["xem_thu"] and h.exists() and h.read_text() == shot["hash"]:
            print(f"[{shot['id']}] không đổi, bỏ qua")
            continue
        print(f"[{shot['id']}] render {shot['so_frame']} khung ({shot['camera']}, {shot['nhan_vat']})")
        render_shot(data, shot, ch, build)


if __name__ == "__main__":
    main()
