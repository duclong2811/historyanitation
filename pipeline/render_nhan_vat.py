"""Chế độ lai, bước render nhân vật: nhân vật VRM (VRoid) render 3D trên nền trong suốt.

Chạy trong Blender (chay.py tự gọi):
    blender -b --factory-startup -P pipeline/render_nhan_vat.py -- build/<tên>/shots.json [--xem-thu] [--may cpu] [--chi s01]

Không cần add-on VRM: file .vrm được nạp bằng bộ nạp glTF có sẵn của Blender, thông tin xương và khẩu hình
đọc bằng pipeline/vrm.py. Mỗi shot:
  - tư thế đứng tự nhiên (hạ tay từ tư thế chữ T), thở, đầu lắc nhẹ
  - động tác theo hanh_dong: vay_tay | chi_tay | gio_cao | gat_dau | dung_yen
  - biểu cảm theo cam_xuc: vui | gian | buon | ngac_nhien | thu_gian
  - nhép miệng theo âm lượng file giọng, chớp mắt tự nhiên
  - shader toon + nét viền vỏ ngược (chạy trên GPU, nhanh hơn Freestyle rất nhiều)
Ra: build/<tên>/nhan_vat/<shot>/f_####.png (RGBA).
"""
import json
import math
import random
import shutil
import sys
import time
import wave
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
GOC = HERE.parent
sys.path.insert(0, str(HERE))
import vrm  # noqa: E402

# Cỡ shot: (chiều cao vùng nhìn thấy theo mét, điểm nhìn: xương, độ lệch lên trên theo mét)
CO_SHOT = {
    "can": (0.72, "head", 0.0),
    "trung": (1.35, "chest", 0.18),
    "rong": (None, "hips", 0.0),   # toàn thân: tính theo chiều cao nhân vật
}
TIEU_CU = 50.0
CAM_XUC = {"vui": "vui", "gian": "gian", "buon": "buon", "ngac_nhien": "ngac_nhien", "thu_gian": "thu_gian"}


def doi_so():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ch = {"shots": None, "xem_thu": "--xem-thu" in a, "may": "gpu", "chi": None}
    for i, x in enumerate(a):
        if x == "--may" and i + 1 < len(a):
            ch["may"] = a[i + 1]
        elif x == "--chi" and i + 1 < len(a):
            ch["chi"] = a[i + 1].split(",")
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
    sc = bpy.context.scene
    r = sc.render
    r.resolution_x, r.resolution_y = data["kho"]
    r.resolution_percentage = 40 if ch["xem_thu"] else data["ty_le_render"]
    r.fps = data["fps"]
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.use_freestyle = False
    if ch["may"] == "cpu":
        r.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = 8 if ch["xem_thu"] else 16
        sc.cycles.use_denoising = True
    else:
        r.engine = engine_eevee()
        sc.eevee.taa_render_samples = 8
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("troi")
    sc.world = w
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.55, 0.55, 0.6, 1)
    bg.inputs["Strength"].default_value = 0.6
    return sc


# ---------- Nạp nhân vật ----------

def nap_vrm(path, build):
    """Nạp .vrm/.glb, trả về (armature, các mesh, thông tin VRM)."""
    p = GOC / path
    info = vrm.doc_vrm(p) if p.suffix.lower() == ".vrm" else {"xuong": {}, "bieu_cam": {}, "huong_mat": "-Y"}
    tam = build / "nhan_vat" / "_nap" / (p.stem + ".glb")
    tam.parent.mkdir(parents=True, exist_ok=True)
    if not tam.exists() or tam.stat().st_mtime < p.stat().st_mtime:
        shutil.copy(p, tam)  # bộ nạp glTF cần đuôi .glb
    truoc = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(tam))
    moi = [o for o in bpy.data.objects if o not in truoc]
    arm = next((o for o in moi if o.type == "ARMATURE"), None)
    if arm is None:
        raise RuntimeError(f"{path} không có khung xương")
    meshes = [o for o in moi if o.type == "MESH"]
    # Bỏ các object phụ không hiện hình (collider, điểm cuối xương tóc...)
    for o in moi:
        if o.type == "EMPTY":
            o.hide_render = True
    goc = bpy.data.objects.new("nhan_vat_goc", None)
    bpy.context.scene.collection.objects.link(goc)
    for o in moi:
        if o.parent is None:
            o.parent = goc
    if info.get("huong_mat") == "+Y":  # VRM 0.x quay lưng về camera: xoay lại
        goc.rotation_euler.z = math.pi
    bpy.context.view_layer.update()
    return arm, meshes, info, goc


def xuong(arm, info, ten):
    """Tìm pose bone theo tên chuẩn humanoid (head, chest...)."""
    t = info["xuong"].get(ten)
    if t and t in arm.pose.bones:
        return arm.pose.bones[t]
    for b in arm.pose.bones:  # dự phòng: đoán theo tên
        if b.name.lower().replace("_", "").replace(" ", "") in (ten.lower(), "j_bip_c_" + ten.lower()):
            return b
    return None


# ---------- Vật liệu toon + nét viền ----------

def _anh_mau(m):
    """Tìm ảnh texture màu của vật liệu (glTF nạp vào thường nối thẳng tới Base Color hoặc Emission)."""
    if not m or not m.use_nodes:
        return None
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            return n
    return None


def doi_sang_toon(meshes):
    xong = {}
    vien = bpy.data.materials.new("net_vien")
    vien.use_nodes = True
    nt = vien.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (0.06, 0.04, 0.04, 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    vien.use_backface_culling = True
    for ob in meshes:
        for i, slot in enumerate(ob.material_slots):
            m = slot.material
            if m is None:
                continue
            if m.name not in xong:
                xong[m.name] = _toon(m)
            slot.material = xong[m.name]
        # Nét viền vỏ ngược: bản sao lưới phình ra, lật mặt, chỉ thấy mép
        n_cu = len(ob.data.materials)
        ob.data.materials.append(vien)
        sd = ob.modifiers.new("net_vien", "SOLIDIFY")
        sd.thickness = 0.0035
        sd.offset = 1.0
        sd.use_flip_normals = True
        sd.use_rim = False
        sd.material_offset = n_cu


def _toon(m_cu):
    tex_cu = _anh_mau(m_cu)
    m = bpy.data.materials.new(m_cu.name + "_toon")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.0, (0.62, 0.56, 0.66, 1)
    el[1].position, el[1].color = 0.18, (1, 1, 1, 1)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    emi = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
    a_mau = next(s for s in mix.inputs if s.identifier == "A_Color")
    b_mau = next(s for s in mix.inputs if s.identifier == "B_Color")
    ra = next(s for s in mix.outputs if s.identifier == "Result_Color")
    nt.links.new(ramp.outputs["Color"], b_mau)
    alpha = None
    if tex_cu:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = tex_cu.image
        tex.interpolation = tex_cu.interpolation
        nt.links.new(tex.outputs["Color"], a_mau)
        alpha = tex.outputs["Alpha"]
    else:
        a_mau.default_value = tuple(m_cu.diffuse_color)
    nt.links.new(ra, emi.inputs["Color"])
    if alpha is not None and m_cu.blend_method != "OPAQUE":
        trong = nt.nodes.new("ShaderNodeBsdfTransparent")
        ms = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(alpha, ms.inputs[0])
        nt.links.new(trong.outputs[0], ms.inputs[1])
        nt.links.new(emi.outputs[0], ms.inputs[2])
        nt.links.new(ms.outputs[0], out.inputs["Surface"])
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
        else:
            m.blend_method = "HASHED"
    else:
        nt.links.new(emi.outputs[0], out.inputs["Surface"])
    m.use_backface_culling = m_cu.use_backface_culling
    return m


# ---------- Tư thế và động tác ----------

def xoay(arm, pb, truc_the_gioi, goc_rad):
    """Xoay xương quanh một trục tính theo thế giới (không phụ thuộc hướng xương của từng mô hình)."""
    if pb is None or goc_rad == 0:
        return
    truc = (arm.matrix_world.inverted().to_3x3() @ Vector(truc_the_gioi)).normalized()
    p = pb.head.copy()
    pb.matrix = Matrix.Translation(p) @ Matrix.Rotation(goc_rad, 4, truc) @ Matrix.Translation(-p) @ pb.matrix
    bpy.context.view_layer.update()


def ben(arm, pb):
    """+1 nếu xương nằm bên +X (thế giới), -1 nếu bên -X."""
    return 1.0 if (arm.matrix_world @ pb.head).x >= 0 else -1.0


def huong_toi(arm, pb, dich):
    """Xoay xương (quanh đầu xương) để hướng đầu→đuôi xương trùng hướng dich (tính theo thế giới).
    Không phụ thuộc mô hình đứng chữ T hay chữ A."""
    if pb is None:
        return
    mw = arm.matrix_world
    hien = (mw @ pb.tail - mw @ pb.head).normalized()
    q = hien.rotation_difference(Vector(dich).normalized())
    truc, goc = q.to_axis_angle()
    if goc > 1e-4:
        xoay(arm, pb, truc, goc)


def _tron(a, b, u):
    return Vector(a).lerp(Vector(b), u).normalized()


# Hướng tay theo thế giới cho nhân vật nhìn về -Y (về phía camera). s = +1 bên +X, -1 bên -X.
def _tay_buong(s, tho):
    return (s * 0.2, 0.06, -1.0), (s * 0.08, -0.25, -1.0 + 0.02 * tho)


def _tay_dong_tac(hd, s, t):
    if hd == "gio_cao":   # giơ cao nắm tay
        return (s * 0.35, -0.15, 1.0), (s * 0.1, -0.1, 1.0)
    if hd == "vay_tay":   # vẫy tay chào
        return (s * 1.0, -0.15, 0.25), (s * (0.15 + 0.35 * math.sin(t * 9)), -0.15, 1.0)
    if hd == "chi_tay":   # chỉ về phía trước
        return (s * 0.12, -1.0, 0.08), (s * 0.06, -1.0, 0.12)
    return None


def dat_tu_the(arm, info, hd, t, n_giay):
    """Đặt tư thế tại thời điểm t (giây), tính lại từ tư thế gốc của mô hình."""
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    X = lambda ten: xuong(arm, info, ten)
    u = min(1.0, t / 0.5)
    u = u * u * (3 - 2 * u)  # vào động tác mượt trong 0.5 giây đầu
    tho = math.sin(t * 2.4)
    xoay(arm, X("spine"), (1, 0, 0), 0.015 * tho)
    xoay(arm, X("chest"), (1, 0, 0), 0.02 * tho)
    xoay(arm, X("neck"), (0, 0, 1), 0.05 * math.sin(t * 0.9))
    xoay(arm, X("head"), (0, 1, 0), 0.03 * math.sin(t * 0.7 + 1))
    if hd == "gat_dau":
        xoay(arm, X("head"), (1, 0, 0), 0.25 * max(0.0, math.sin(t * 6.0)) * u)
    for phia in ("left", "right"):
        tren, duoi = X(phia + "UpperArm"), X(phia + "LowerArm")
        if tren is None:
            continue
        s = ben(arm, tren)
        buong_tren, buong_duoi = _tay_buong(s, tho)
        dt = _tay_dong_tac(hd, s, t) if phia == "right" else None
        if dt:
            huong_toi(arm, tren, _tron(buong_tren, dt[0], u))
            huong_toi(arm, duoi, _tron(buong_duoi, dt[1], u))
        else:
            huong_toi(arm, tren, buong_tren)
            huong_toi(arm, duoi, buong_duoi)


# ---------- Động tác Mixamo ----------

# Tên xương Mixamo -> tên xương humanoid VRM
MIXAMO = {
    "Hips": "hips", "Spine": "spine", "Spine1": "chest", "Spine2": "upperChest", "Neck": "neck", "Head": "head",
    "LeftShoulder": "leftShoulder", "LeftArm": "leftUpperArm", "LeftForeArm": "leftLowerArm", "LeftHand": "leftHand",
    "RightShoulder": "rightShoulder", "RightArm": "rightUpperArm", "RightForeArm": "rightLowerArm",
    "RightHand": "rightHand", "LeftUpLeg": "leftUpperLeg", "LeftLeg": "leftLowerLeg", "LeftFoot": "leftFoot",
    "RightUpLeg": "rightUpperLeg", "RightLeg": "rightLowerLeg", "RightFoot": "rightFoot",
}
# Xương chỉ khớp hướng (tay, chân); còn lại khớp góc xoay theo thế giới (thân, đầu, bàn tay, bàn chân)
KHOP_HUONG = {"leftUpperArm", "leftLowerArm", "rightUpperArm", "rightLowerArm",
              "leftUpperLeg", "leftLowerLeg", "rightUpperLeg", "rightLowerLeg"}
THU_TU = ["hips", "spine", "chest", "upperChest", "neck", "head",
          "leftShoulder", "leftUpperArm", "leftLowerArm", "leftHand",
          "rightShoulder", "rightUpperArm", "rightLowerArm", "rightHand",
          "leftUpperLeg", "leftLowerLeg", "leftFoot", "rightUpperLeg", "rightLowerLeg", "rightFoot"]


def tep_dong_tac(hd):
    """assets/dong_tac/<hanh_dong>.fbx nếu có (động tác tải từ Mixamo)."""
    p = GOC / "assets" / "dong_tac" / f"{hd}.fbx"
    return p if hd and p.exists() else None


def nap_mixamo(path):
    """Nạp FBX Mixamo, trả về (armature nguồn, {tên humanoid: pose bone}, (khung đầu, khung cuối))."""
    truoc = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
    moi = [o for o in bpy.data.objects if o not in truoc]
    nguon = next((o for o in moi if o.type == "ARMATURE"), None)
    if nguon is None or not nguon.animation_data or not nguon.animation_data.action:
        raise RuntimeError(f"{path.name} không có khung xương hoặc không có chuyển động")
    for o in moi:
        o.hide_render = True
        o.hide_viewport = False
    xg = {}
    for pb in nguon.pose.bones:
        ten = pb.name.split(":")[-1]
        if ten in MIXAMO:
            xg[MIXAMO[ten]] = pb
    if "hips" not in xg:
        raise RuntimeError(f"{path.name} không giống khung xương Mixamo (thiếu Hips)")
    bpy.context.view_layer.update()
    # Cho nhân vật nguồn nhìn về -Y như nhân vật VRM: bên trái nằm phía +X
    tr, ph = xg.get("leftUpperArm"), xg.get("rightUpperArm")
    if tr and ph and (nguon.matrix_world @ tr.head).x < (nguon.matrix_world @ ph.head).x:
        goc = bpy.data.objects.new("nguon_goc", None)
        bpy.context.scene.collection.objects.link(goc)
        nguon.parent = goc
        goc.rotation_euler.z = math.pi
        bpy.context.view_layer.update()
    a, b = nguon.animation_data.action.frame_range
    return nguon, xg, (int(a), int(b))


def _quay_the_gioi(obj, pb, nghi=False):
    m = obj.matrix_world @ (pb.bone.matrix_local if nghi else pb.matrix)
    return m.to_quaternion()


def dat_tu_the_mixamo(arm, info, nguon, xg, f_nguon):
    """Chép tư thế khung f_nguon của động tác Mixamo sang nhân vật VRM."""
    sc = bpy.context.scene
    sc.frame_set(f_nguon)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    q_arm = arm.matrix_world.to_quaternion()
    for ten in THU_TU:
        s, d = xg.get(ten), xuong(arm, info, ten)
        if s is None or d is None:
            continue
        if ten in KHOP_HUONG:
            mw = nguon.matrix_world
            huong_toi(arm, d, mw @ s.tail - mw @ s.head)
            continue
        delta = _quay_the_gioi(nguon, s) @ _quay_the_gioi(nguon, s, nghi=True).inverted()
        muon = delta @ _quay_the_gioi(arm, d, nghi=True)
        quay = (q_arm.inverted() @ muon).to_matrix().to_4x4()
        d.matrix = Matrix.Translation(d.matrix.translation) @ quay
        bpy.context.view_layer.update()
    # Hông: chép cả độ nhún lên xuống, tỉ lệ theo chiều cao hông
    s, d = xg["hips"], xuong(arm, info, "hips")
    if d is not None:
        mw = nguon.matrix_world
        cao_nguon = max(1e-3, (mw @ s.bone.head_local).z)
        cao_dich = max(1e-3, (arm.matrix_world @ d.bone.head_local).z)
        lech = ((mw @ s.head) - (mw @ s.bone.head_local)) * (cao_dich / cao_nguon)
        lech = arm.matrix_world.inverted().to_3x3() @ lech
        d.matrix = Matrix.Translation(d.matrix.translation + lech) @ d.matrix.to_3x3().to_4x4()
        bpy.context.view_layer.update()


def ghi_khung(arm, f):
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler", frame=f)


# ---------- Biểu cảm, khẩu hình, chớp mắt ----------

def tim_bieu_cam(meshes, info):
    """chuẩn -> [(key_block, trọng số)]"""
    theo_ten = {}
    for ob in meshes:
        theo_ten.setdefault(ob.data.name, ob)
        theo_ten.setdefault(ob.name, ob)
    ket = {}
    for chuan, binds in info.get("bieu_cam", {}).items():
        ds = []
        for ten_mesh, idx, w in binds:
            ob = theo_ten.get(ten_mesh)
            if ob and ob.data.shape_keys and idx + 1 < len(ob.data.shape_keys.key_blocks):
                ds.append((ob.data.shape_keys.key_blocks[idx + 1], w))
        if ds:
            ket[chuan] = ds
    return ket


def am_luong(wav_path, fps, n):
    """Âm lượng (0..1) của file giọng theo từng khung hình."""
    if not wav_path or not Path(wav_path).exists():
        return [0.0] * n
    with wave.open(str(wav_path), "rb") as w:
        sr, kenh, rong = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    import array
    a = array.array("h", raw) if rong == 2 else array.array("h")
    if kenh > 1:
        a = a[::kenh]
    buoc = sr / fps
    ds = []
    for i in range(n):
        doan = a[int(i * buoc):int((i + 1) * buoc)]
        ds.append(math.sqrt(sum(x * x for x in doan) / len(doan)) if doan else 0.0)
    dinh = sorted(ds)[int(len(ds) * 0.95)] if ds else 1.0
    return [min(1.0, x / max(dinh, 1.0)) for x in ds]


def bieu_cam_tung_khung(bc, shot, fps, wav_path):
    n = shot["so_frame"]
    rnd = random.Random(shot["id"])
    am = am_luong(wav_path, fps, n) if shot.get("dang_noi") else [0.0] * n
    nguyen_am = ["a", "o", "a", "e", "a", "i", "u"]
    chop = set()
    t = rnd.uniform(0.6, 1.6)
    while t * fps < n:
        k = int(t * fps)
        chop.update({k, k + 1, k + 2})
        t += rnd.uniform(2.0, 4.5)
    cx = CAM_XUC.get(shot.get("cam_xuc", ""), None)
    gia_tri = []
    mieng_cu, nam_cu = 0.0, "a"
    for f in range(n):
        v = {k: 0.0 for k in bc}
        mo = 0.55 * mieng_cu + 0.45 * am[f]  # làm mượt để miệng không giật
        mieng_cu = mo
        if mo > 0.12:
            if f % 4 == 0:
                nam_cu = rnd.choice(nguyen_am)
            v[nam_cu] = min(1.0, mo * 1.15)
        if cx in bc:
            v[cx] = 0.7
        if f in chop and "chop_mat" in bc and cx not in ("vui",):
            v["chop_mat"] = 1.0 if (f - 1) in chop and (f + 1) in chop else 0.6
        gia_tri.append(v)
    return gia_tri


def ghi_bieu_cam(bc, gia_tri, buoc):
    for f in range(0, len(gia_tri), buoc):
        for chuan, ds in bc.items():
            for kb, w in ds:
                kb.value = gia_tri[f].get(chuan, 0.0) * w
                kb.keyframe_insert("value", frame=f + 1)


# ---------- Camera, ánh sáng ----------

def dat_camera(arm, info, shot, data):
    X = lambda ten: xuong(arm, info, ten)
    the_gioi = lambda pb: arm.matrix_world @ pb.head
    dau = X("head")
    if dau is None:
        raise RuntimeError("không tìm thấy xương đầu (head) trong mô hình")
    z_dau = the_gioi(dau).z
    cao_vung, ten_x, len_tren = CO_SHOT.get(shot.get("camera", "trung"), CO_SHOT["trung"])
    if cao_vung is None:
        cao_vung = (z_dau + 0.2) * 1.15
        muc = Vector((the_gioi(dau).x, the_gioi(dau).y, (z_dau + 0.2) / 2))
    else:
        pb = X(ten_x) or dau
        muc = the_gioi(pb) + Vector((0, 0, len_tren))
        if ten_x == "head":
            muc.z = z_dau + 0.1
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = TIEU_CU
    cam_d.sensor_fit = "VERTICAL"
    cam_d.sensor_height = 24.0
    w, h = data["kho"]
    if w > h:
        cam_d.sensor_fit = "HORIZONTAL"
        cam_d.sensor_width = 36.0
    fov = 2 * math.atan(12.0 / TIEU_CU) if w <= h else 2 * math.atan(18.0 / TIEU_CU) * h / w
    dist = (cao_vung / 2) / math.tan(fov / 2)
    goc = math.radians(shot.get("goc_quay", 12))
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = muc + Vector((math.sin(goc) * dist, -math.cos(goc) * dist, 0.0))
    huong = muc - cam.location
    cam.rotation_euler = huong.to_track_quat("-Z", "Y").to_euler()
    # Vị trí nhân vật ngang khung hình: 0 = mép trái, 1 = mép phải
    x = float(shot.get("vi_tri", 0.5))
    cam_d.shift_x = (0.5 - x) * (min(w, h) / max(w, h) if w <= h else 1.0)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam


def anh_sang(mau_nang=(1.0, 0.94, 0.85)):
    for ten, rot, manh, mau in (("nang", (math.radians(55), 0, math.radians(-35)), 3.0, mau_nang),
                                ("vien", (math.radians(70), 0, math.radians(160)), 2.5, (1.0, 0.9, 0.75))):
        l = bpy.data.lights.new(ten, "SUN")
        l.energy, l.color = manh, mau
        ob = bpy.data.objects.new(ten, l)
        ob.rotation_euler = rot
        bpy.context.scene.collection.objects.link(ob)


# ---------- Render ----------

def render_shot(data, shot, ch, build):
    sc = lam_moi(data, ch)
    nv = shot["tren_hinh"][0]
    cfg = data["nhan_vat"][nv]
    arm, meshes, info, _goc = nap_vrm(cfg["mo_hinh"], build)
    doi_sang_toon(meshes)
    anh_sang()
    fps, n = data["fps"], shot["so_frame"]
    buoc = 2 if data["on_twos"] else 1
    bc = tim_bieu_cam(meshes, info)
    wav = GOC / shot["giong"] if shot.get("giong") else None
    gia_tri = bieu_cam_tung_khung(bc, shot, fps, wav)
    ds_khung = [max(1, n // 2)] if ch["xem_thu"] else list(range(1, n + 1, buoc))
    hd = shot.get("hanh_dong", "dung_yen")
    fbx = tep_dong_tac(hd)
    if fbx:  # động tác Mixamo: lặp lại nếu shot dài hơn động tác
        nguon, xg, (a, b) = nap_mixamo(fbx)
        dai = max(1, b - a)
        for f in ds_khung:
            dat_tu_the_mixamo(arm, info, nguon, xg, a + (f - 1) % dai)
            ghi_khung(arm, f)
        print(f"  động tác Mixamo: {fbx.name} ({dai} khung)", flush=True)
    else:
        for f in ds_khung:
            dat_tu_the(arm, info, hd, (f - 1) / fps, n / fps)
            ghi_khung(arm, f)
    ghi_bieu_cam(bc, gia_tri, 1 if ch["xem_thu"] else buoc)
    sc.frame_set(ds_khung[0])
    dat_camera(arm, info, shot, data)
    sc.frame_start, sc.frame_end, sc.frame_step = 1, n, buoc
    if ch["xem_thu"]:
        out = build / "nhan_vat" / "xem_thu"
        out.mkdir(parents=True, exist_ok=True)
        sc.frame_set(ds_khung[0])
        sc.render.filepath = str(out / f"{shot['id']}.png")
        bpy.ops.render.render(write_still=True)
        return
    out = build / "nhan_vat" / shot["id"]
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    sc.render.filepath = str(out / "f_")
    bpy.ops.render.render(animation=True)
    (out / ".hash").write_text(shot["hash_nv"])


def main():
    ch = doi_so()
    path = Path(ch["shots"])
    if not path.is_absolute():
        path = GOC / path
    data = json.loads(path.read_text(encoding="utf-8"))
    build = path.parent
    for shot in data["shots"]:
        if not shot.get("tren_hinh") or (ch["chi"] and shot["id"] not in ch["chi"]):
            continue
        h = build / "nhan_vat" / shot["id"] / ".hash"
        if not ch["xem_thu"] and h.exists() and h.read_text() == shot["hash_nv"]:
            print(f"[{shot['id']}] không đổi, bỏ qua")
            continue
        print(f"[{shot['id']}] render {shot['so_frame']} khung ({shot.get('camera')}, {shot['tren_hinh'][0]})",
              flush=True)
        t0 = time.time()
        render_shot(data, shot, ch, build)
        so = 1 if ch["xem_thu"] else (shot["so_frame"] + 1) // 2 if data["on_twos"] else shot["so_frame"]
        dt = time.time() - t0
        print(f"[{shot['id']}] xong trong {dt:.0f} giây, trung bình {dt / so:.1f} giây/khung", flush=True)


if __name__ == "__main__":
    main()
