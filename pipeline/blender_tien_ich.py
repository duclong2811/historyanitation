"""Hàm dựng hình dùng trong Blender: vật liệu toon, khối cơ bản, cây cối, thuyền, người, trời.

Chỉ import được bên trong Blender (cần bpy). Script dựng cảnh trong canh/ dùng các hàm này.
Quy ước: Z hướng lên, đơn vị mét. Nhân vật huong=0 nhìn về phía -Y.
"""
import math
import random
import urllib.request
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

GOC = Path(__file__).resolve().parent.parent

# render_blender.py đặt các giá trị này trước khi dựng cảnh
ENGINE = "EEVEE"   # "EEVEE" hoặc "CYCLES"
SO_FRAME = 60      # số khung của shot
FPS = 30
_VAT_LIEU = {}


# ---------------- Màu và vật liệu ----------------

def mau_rgb(hex_mau):
    """'#b5462f' -> (r, g, b, 1) trong không gian màu linear của Blender."""
    h = hex_mau.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, 1.0)


def _socket(node, kieu, ten):
    for s in (node.inputs if kieu == "in" else node.outputs):
        if s.identifier == ten or s.name == ten:
            return s
    raise KeyError(ten)


def vat_lieu(hex_mau, phat_sang=0.0):
    """Vật liệu toon: Eevee dùng Shader to RGB + ColorRamp 3 nấc; Cycles dùng diffuse phẳng.
    phat_sang > 0: tự phát sáng (đèn lồng, lửa)."""
    key = (hex_mau, phat_sang, ENGINE)
    if key in _VAT_LIEU:
        return _VAT_LIEU[key]
    m = bpy.data.materials.new(f"toon_{hex_mau.lstrip('#')}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mau = mau_rgb(hex_mau)
    if phat_sang > 0:
        emi = nt.nodes.new("ShaderNodeEmission")
        emi.inputs["Color"].default_value = mau
        emi.inputs["Strength"].default_value = phat_sang
        nt.links.new(emi.outputs[0], out.inputs["Surface"])
    elif ENGINE == "EEVEE":
        diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
        diff.inputs["Color"].default_value = (1, 1, 1, 1)
        s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        e = ramp.color_ramp.elements
        e[0].position, e[0].color = 0.0, (0.40, 0.40, 0.55, 1)   # bóng: tím lạnh
        e[1].position, e[1].color = 0.12, (0.72, 0.70, 0.80, 1)  # bán bóng
        e.new(0.45).color = (1, 1, 1, 1)                         # sáng
        e.new(0.95).color = (1.25, 1.18, 1.05, 1)                # chỗ sáng gắt (đèn viền)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        _socket(mix, "in", "Factor_Float").default_value = 1.0
        _socket(mix, "in", "A_Color").default_value = mau
        emi = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(diff.outputs[0], s2r.inputs[0])
        nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], _socket(mix, "in", "B_Color"))
        nt.links.new(_socket(mix, "out", "Result_Color"), emi.inputs["Color"])
        nt.links.new(emi.outputs[0], out.inputs["Surface"])
    else:
        diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
        diff.inputs["Color"].default_value = mau
        nt.links.new(diff.outputs[0], out.inputs["Surface"])
    m.diffuse_color = mau
    _VAT_LIEU[key] = m
    return m


# ---------------- Ghép lưới nhiều phần, nhiều màu ----------------

class Luoi:
    """Gom nhiều khối vào một lưới (một object), mỗi khối một màu.
        l = Luoi(); l.tru(...); l.khoi(...); ob = l.tao("ten", vi_tri)"""

    def __init__(self):
        self.bm = bmesh.new()
        self.mau = []

    def _gan(self, verts, mau):
        if mau not in self.mau:
            self.mau.append(mau)
        idx = self.mau.index(mau)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = idx

    def khoi(self, kich_thuoc, tam_day, mau, xoay=(0, 0, 0)):
        sx, sy, sz = kich_thuoc
        M = (Matrix.Translation(tam_day) @ _xoay(xoay) @ Matrix.Diagonal((sx, sy, sz, 1))
             @ Matrix.Translation((0, 0, 0.5)))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._gan(r["verts"], mau)

    def tru(self, r_duoi, r_tren, cao, tam_day, mau, canh=12, xoay=(0, 0, 0)):
        M = Matrix.Translation(tam_day) @ _xoay(xoay) @ Matrix.Translation((0, 0, cao / 2))
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=canh, radius1=r_duoi,
                                  radius2=max(r_tren, 1e-4), depth=cao, matrix=M)
        self._gan(r["verts"], mau)

    def cau(self, ban_kinh, tam, mau, ty_le=(1, 1, 1), phan=(16, 10)):
        M = Matrix.Translation(tam) @ Matrix.Diagonal((*ty_le, 1))
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=phan[0], v_segments=phan[1],
                                      radius=ban_kinh, matrix=M)
        self._gan(r["verts"], mau)

    def mat(self, diem, mau):
        """Một mặt đa giác từ danh sách điểm."""
        vs = [self.bm.verts.new(p) for p in diem]
        self.bm.faces.new(vs)
        self._gan(vs, mau)

    def dai(self, hang, mau, dong_dau=False, dong_cuoi=False):
        """Mặt cong nối các hàng điểm (mỗi hàng là một mặt cắt cùng số điểm)."""
        luoi = [[self.bm.verts.new(p) for p in h] for h in hang]
        for a, b in zip(luoi, luoi[1:]):
            for i in range(len(a) - 1):
                self.bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
        if dong_dau and len(luoi[0]) > 2:
            self.bm.faces.new(luoi[0][::-1])
        if dong_cuoi and len(luoi[-1]) > 2:
            self.bm.faces.new(luoi[-1])
        self._gan([v for h in luoi for v in h], mau)

    def tao(self, ten, vi_tri=(0, 0, 0), huong=0.0, cha=None, muot=False):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        # Bỏ mặt suy biến (trùng cạnh sau khi gộp điểm), tránh Blender in cảnh báo "edge appears twice"
        bmesh.ops.dissolve_degenerate(self.bm, dist=1e-5, edges=self.bm.edges)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(ten)
        self.bm.to_mesh(me)
        self.bm.free()
        for p in me.polygons:
            p.use_smooth = muot
        for m in self.mau:
            me.materials.append(vat_lieu(m))
        ob = bpy.data.objects.new(ten, me)
        ob.location = vi_tri
        ob.rotation_euler.z = huong
        bpy.context.scene.collection.objects.link(ob)
        if cha:
            ob.parent = cha
        return ob


def _xoay(xoay):
    return (Matrix.Rotation(xoay[2], 4, "Z") @ Matrix.Rotation(xoay[1], 4, "Y")
            @ Matrix.Rotation(xoay[0], 4, "X"))


# ---------------- Khối đơn (giữ cho cảnh cũ dùng) ----------------

def khoi(ten, kich_thuoc, vi_tri, mau, xoay_z=0.0, cha=None):
    """Khối hộp. kich_thuoc = (rộng x, sâu y, cao z); vi_tri là tâm đáy."""
    l = Luoi()
    l.khoi(kich_thuoc, (0, 0, 0), mau)
    return l.tao(ten, vi_tri, xoay_z, cha)


def tru(ten, r_duoi, r_tren, cao, vi_tri, mau, canh=16, cha=None, dich_z=0.5):
    """Khối trụ hoặc nón. dich_z=0.5: gốc ở đáy; dich_z=-0.5: gốc ở đỉnh (dùng cho tay treo)."""
    l = Luoi()
    l.tru(r_duoi, r_tren, cao, (0, 0, cao * (dich_z - 0.5)), mau, canh)
    return l.tao(ten, vi_tri, 0.0, cha, muot=True)


def cau(ten, ban_kinh, vi_tri, mau, ty_le=(1, 1, 1), cha=None):
    l = Luoi()
    l.cau(ban_kinh, (0, 0, 0), mau, ty_le, (24, 16))
    return l.tao(ten, vi_tri, 0.0, cha, muot=True)


def lang_tru_mai(ten, rong, sau, cao, vi_tri, mau, nho_ra=0.3, xoay_z=0.0):
    """Mái hai dốc (lăng trụ tam giác), vi_tri là tâm đáy mái."""
    l = Luoi()
    _mai(l, rong, sau, cao, (0, 0, 0), mau, nho_ra)
    return l.tao(ten, vi_tri, xoay_z)


def _mai(l, rong, sau, cao, goc, mau, nho_ra):
    x, y = rong / 2 + nho_ra, sau / 2 + nho_ra
    gx, gy, gz = goc
    p = [(gx + a, gy + b, gz + c) for a, b, c in
         [(-x, -y, 0), (x, -y, 0), (0, -y, cao), (-x, y, 0), (x, y, 0), (0, y, cao)]]
    l.mat([p[0], p[1], p[2]], mau)
    l.mat([p[5], p[4], p[3]], mau)
    l.mat([p[1], p[4], p[5], p[2]], mau)
    l.mat([p[3], p[0], p[2], p[5]], mau)
    l.mat([p[0], p[3], p[4], p[1]], mau)


def ban_sao(ob, ten, vi_tri, ty_le=1.0, xoay_z=0.0):
    """Bản sao dùng chung lưới (instancing): 1.000 cây chỉ tốn bộ nhớ như 1 cây."""
    c = ob.copy()
    c.name = ten
    c.location = vi_tri
    c.scale = (ty_le, ty_le, ty_le)
    c.rotation_euler.z = xoay_z
    bpy.context.scene.collection.objects.link(c)
    return c


# ---------------- Trời, nắng, sương ----------------

def hdri(ten, do_sang=1.0, xoay_do=0.0, do_phan_giai="1k"):
    """Bầu trời HDRI từ Poly Haven (CC0). Tự tải về assets/hdri/ lần đầu."""
    tep = GOC / "assets" / "hdri" / f"{ten}_{do_phan_giai}.hdr"
    if not tep.exists():
        tep.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/{do_phan_giai}/{tep.name}"
        print(f"  Tải HDRI {tep.name}...")
        urllib.request.urlretrieve(url, tep)
    w = bpy.context.scene.world
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(tep), check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value[2] = math.radians(xoay_do)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = do_sang
    return w


def suong(mat_do=0.008, mau="#e8d6c0", kich_thuoc=(400, 400, 60), tam=(0, 0, 0)):
    """Sương mù: một khối volume lớn bao quanh cảnh, làm hậu cảnh nhạt dần cho có chiều sâu.
    (Không đặt volume ở world: Eevee coi world volume dày vô hạn nên che mất bầu trời.)"""
    m = bpy.data.materials.new("suong")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vs = nt.nodes.new("ShaderNodeVolumeScatter")
    vs.inputs["Color"].default_value = mau_rgb(mau)
    vs.inputs["Density"].default_value = mat_do
    nt.links.new(vs.outputs[0], out.inputs["Volume"])
    l = Luoi()
    l.khoi(kich_thuoc, (tam[0], tam[1], tam[2] - 1), "#ffffff")
    ob = l.tao("khoi_suong")
    ob.data.materials[0] = m
    ob.visible_shadow = False
    return ob


def mat_troi(cao_do=20, huong_do=30, mau="#ffc48a", manh=3.0):
    """Chỉnh đèn mặt trời mặc định của cảnh."""
    ob = bpy.data.objects.get("mat_troi")
    ob.rotation_euler = (math.radians(90 - cao_do), 0, math.radians(huong_do))
    ob.data.color = mau_rgb(mau)[:3]
    ob.data.energy = manh
    return ob


def den_vien(cao_do=15, huong_do=200, mau="#ffd9a0", manh=2.0):
    """Đèn viền chiếu từ phía sau, làm sáng mép nhân vật cho tách khỏi nền."""
    l = bpy.data.lights.new("den_vien", "SUN")
    l.color = mau_rgb(mau)[:3]
    l.energy = manh
    ob = bpy.data.objects.new("den_vien", l)
    ob.rotation_euler = (math.radians(90 - cao_do), 0, math.radians(huong_do))
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------- Chuyển động ----------------

def dap_dinh(ob, bien_do=0.03, nhip=0.6, pha=0.0, buoc=3):
    """Bập bềnh trên sóng: nhấp nhô và nghiêng nhẹ."""
    z0 = ob.location.z
    for f in range(1, SO_FRAME + 2, buoc):
        t = f / FPS * nhip * math.tau + pha
        ob.location.z = z0 + bien_do * math.sin(t)
        ob.keyframe_insert("location", index=2, frame=f)
        ob.rotation_euler.x = bien_do * 0.8 * math.sin(t + 1.3)
        ob.keyframe_insert("rotation_euler", index=0, frame=f)
    ob.location.z = z0


# ---------------- Cây cối ----------------

def _la_dai(l, goc, huong, dai, rong, nghieng, cong, mau, doan=7):
    """Một tàu lá dài cong (dừa, dừa nước): dải hẹp hai đầu, rủ xuống."""
    gx, gy, gz = goc
    dx, dy = math.cos(huong), math.sin(huong)
    hang = []
    for i in range(doan + 1):
        s = i / doan
        r = dai * s
        z = r * math.sin(nghieng) - cong * dai * s * s
        x = gx + dx * r * math.cos(nghieng)
        y = gy + dy * r * math.cos(nghieng)
        w = rong * math.sin(math.pi * min(0.98, s * 0.85 + 0.08)) / 2
        hang.append([(x - dy * w, y + dx * w, gz + z), (x, y, gz + z + w * 0.3), (x + dy * w, y - dx * w, gz + z)])
    l.dai(hang, mau)


def dua_nuoc(ten="dua_nuoc", mau="#5f8a3a", so_la=11, seed=1):
    """Bụi dừa nước: lá mọc thẳng từ gốc ven nước. Trả về object mẫu để ban_sao()."""
    rnd = random.Random(seed)
    l = Luoi()
    for i in range(so_la):
        _la_dai(l, (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0), rnd.uniform(0, math.tau),
                rnd.uniform(3.5, 5.0), 0.5, math.radians(rnd.uniform(48, 72)), rnd.uniform(0.25, 0.45), mau)
    return _khong_net(l.tao(ten))


def cay_dua(ten="cay_dua", cao=8.0, mau_than="#8a7458", mau_la="#4e7d32", so_la=12, seed=2):
    """Cây dừa: thân cong nhẹ, tán lá rủ."""
    rnd = random.Random(seed)
    l = Luoi()
    doan = 6
    cong = rnd.uniform(0.4, 0.9)
    for i in range(doan):
        z0, z1 = cao * i / doan, cao * (i + 1) / doan
        x0 = cong * (z0 / cao) ** 2
        l.tru(0.2 - 0.06 * i / doan, 0.2 - 0.06 * (i + 1) / doan, z1 - z0, (x0, 0, z0), mau_than, canh=8)
    dinh = (cong, 0, cao)
    for i in range(so_la):
        _la_dai(l, dinh, i / so_la * math.tau + rnd.uniform(-0.2, 0.2), rnd.uniform(3.2, 4.2), 0.7,
                math.radians(rnd.uniform(15, 40)), rnd.uniform(0.35, 0.55), mau_la)
    l.cau(0.35, dinh, mau_la)
    return _khong_net(l.tao(ten))


def bui_co(ten="bui_co", mau="#7f9a4a", seed=3):
    """Bụi cỏ lác ven bờ."""
    rnd = random.Random(seed)
    l = Luoi()
    for i in range(9):
        _la_dai(l, (rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), 0), rnd.uniform(0, math.tau),
                rnd.uniform(0.8, 1.3), 0.08, math.radians(rnd.uniform(60, 80)), 0.2, mau, doan=4)
    return _khong_net(l.tao(ten))


def _khong_net(ob):
    """Đánh dấu object không vẽ nét viền (bản sao bằng ban_sao giữ luôn dấu này)."""
    ob["khong_net"] = True
    return ob


# ---------------- Công trình ----------------

def coc_rao(ten="coc_rao", cao=2.4, mau="#7a5b3a"):
    """Một cọc rào vót nhọn (mẫu để ban_sao)."""
    l = Luoi()
    l.tru(0.09, 0.09, cao - 0.35, (0, 0, 0), mau, canh=7)
    l.tru(0.09, 0.0, 0.35, (0, 0, cao - 0.35), mau, canh=7)
    return l.tao(ten)


def hang_rao(mau_coc, diem_dau, diem_cuoi, khoang=0.2, ten="rao", seed=4):
    """Hàng cọc rào từ diem_dau tới diem_cuoi (x, y, z)."""
    rnd = random.Random(seed)
    a, b = Vector(diem_dau), Vector(diem_cuoi)
    n = max(1, int((b - a).length / khoang))
    for i in range(n + 1):
        p = a.lerp(b, i / n)
        c = ban_sao(mau_coc, f"{ten}_{i}", p, rnd.uniform(0.85, 1.1), rnd.uniform(0, math.tau))
        c.rotation_euler.x = rnd.uniform(-0.05, 0.05)


def nha_la(ten, rong, sau, cao_vach, vi_tri, huong=0.0, mau_vach="#b08a5a", mau_mai="#8c7a4a",
           mau_cua="#4a3420", nha_san=0.0):
    """Nhà lá: vách tre/ván, mái lá dốc. nha_san > 0: dựng trên cột cao chừng ấy mét."""
    l = Luoi()
    z = nha_san
    if nha_san > 0:
        for sx in (-1, 1):
            for sy in (-1, 1):
                l.tru(0.08, 0.08, nha_san, (sx * (rong / 2 - 0.15), sy * (sau / 2 - 0.15), 0), mau_vach, canh=6)
        l.khoi((rong + 0.4, sau + 0.4, 0.1), (0, 0, z - 0.1), mau_vach)
    l.khoi((rong, sau, cao_vach), (0, 0, z), mau_vach)
    l.khoi((rong * 0.28, 0.06, cao_vach * 0.75), (0, -sau / 2 - 0.02, z), mau_cua)
    _mai(l, rong, sau, cao_vach * 1.0, (0, 0, z + cao_vach), mau_mai, nho_ra=0.5)
    return l.tao(ten, vi_tri, huong)


def choi_canh(ten, vi_tri, cao=5.0, mau_cot="#6e5233", mau_mai="#8c7a4a"):
    """Chòi canh: bốn cột cao, sàn, lan can, mái lá nhọn."""
    l = Luoi()
    r = 1.1
    for sx in (-1, 1):
        for sy in (-1, 1):
            l.tru(0.1, 0.08, cao + 2.3, (sx * r, sy * r, 0), mau_cot, canh=6)
    l.khoi((2 * r + 0.4, 2 * r + 0.4, 0.15), (0, 0, cao), mau_cot)
    for sy in (-1, 1):
        l.khoi((2 * r + 0.4, 0.08, 0.9), (0, sy * (r + 0.16), cao + 0.15), mau_cot)
    l.khoi((0.08, 2 * r + 0.4, 0.9), (r + 0.16, 0, cao + 0.15), mau_cot)
    l.tru(r * 1.9, 0.0, 1.5, (0, 0, cao + 2.3), mau_mai, canh=4, xoay=(0, 0, math.pi / 4))
    return l.tao(ten, vi_tri)


def co(ten, vi_tri, mau="#a8322a", cao=5.0, rong=1.6, dai=1.1, mau_can="#5a4128"):
    """Cột cờ với lá cờ bay trong gió (modifier Wave tự chuyển động theo khung hình)."""
    can = tru(f"{ten}_can", 0.05, 0.04, cao, vi_tri, mau_can, canh=6)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=14, y_segments=6, size=0.5,
                          matrix=Matrix.Translation((rong / 2, 0, 0)) @ Matrix.Diagonal((rong, dai, 1, 1)))
    me = bpy.data.meshes.new(f"{ten}_la")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(vat_lieu(mau))
    la = bpy.data.objects.new(f"{ten}_la", me)
    la.location = (0.04, 0, cao - dai / 2 - 0.1)
    la.rotation_euler.x = math.pi / 2
    la.parent = can
    bpy.context.scene.collection.objects.link(la)
    w = la.modifiers.new("gio", "WAVE")
    w.use_y, w.use_x = False, True
    w.height, w.width, w.speed = 0.09, 0.55, 0.06
    w.start_position_x = 0.0
    return can


# ---------------- Thuyền ----------------

def thuyen(ten, vi_tri, huong=0.0, dai=12.0, rong=2.6, cao=1.1, mau_than="#6b4a2c", mau_mui="#9c8355",
           mau_buom="#b7955f", mau_mat="#f2efe6", so_buom=2, so_mai_cheo=6):
    """Thuyền chiến gỗ: thân cong hai đầu cong lên, mui giữa, buồm cói có thanh nẹp, mắt thuyền, mái chèo.
    Mũi thuyền ở phía +X (trước khi xoay huong)."""
    l = Luoi()
    tram = 12
    hang = []
    for i in range(tram + 1):
        s = -0.97 + 1.94 * i / tram
        w = rong / 2 * (1 - s * s) ** 0.55
        z_boong = cao * (0.75 + 0.55 * s ** 4) + (0.35 * s ** 6 if s > 0 else 0.2 * s ** 6)
        z_day = -cao * 0.35 * (1 - s * s) ** 0.5 + cao * 0.5 * s ** 4
        x = s * dai / 2
        hang.append([(x, -w, z_boong), (x, -w * 0.9, z_day * 0.4 + z_boong * 0.2), (x, 0, z_day),
                     (x, w * 0.9, z_day * 0.4 + z_boong * 0.2), (x, w, z_boong)])
    l.dai(hang, mau_than, dong_dau=True, dong_cuoi=True)
    # Sàn boong
    boong = [h[0] for h in hang] + [h[4] for h in hang][::-1]
    l.mat([(p[0], p[1], p[2] - 0.04) for p in boong], "#8a6a45")
    # Mui thuyền (vòm che giữa thân)
    l_mui = dai * 0.26
    for i in range(7):
        a0, a1 = math.pi * i / 7, math.pi * (i + 1) / 7
        r = rong * 0.42
        p = [(-l_mui / 2, math.cos(a0) * r, cao * 0.8 + math.sin(a0) * r * 0.85),
             (l_mui / 2, math.cos(a0) * r, cao * 0.8 + math.sin(a0) * r * 0.85),
             (l_mui / 2, math.cos(a1) * r, cao * 0.8 + math.sin(a1) * r * 0.85),
             (-l_mui / 2, math.cos(a1) * r, cao * 0.8 + math.sin(a1) * r * 0.85)]
        l.mat(p, mau_mui)
    # Cột buồm và buồm cói nhiều thanh nẹp (buồm dọc theo thân thuyền)
    for k in range(so_buom):
        x = dai * (0.22 - 0.42 * k / max(1, so_buom - 1)) if so_buom > 1 else dai * 0.1
        cao_cot = cao + dai * (0.62 if k == 0 else 0.5)
        l.tru(0.08, 0.06, cao_cot, (x, 0, cao * 0.6), "#4f3a24", canh=6)
        b_rong, b_cao = dai * 0.3, dai * (0.42 if k == 0 else 0.34)
        z0 = cao_cot + cao * 0.6 - b_cao - 0.2
        l.mat([(x - b_rong * 0.75, 0.05, z0), (x + b_rong * 0.25, 0.05, z0),
               (x + b_rong * 0.3, 0.05, z0 + b_cao), (x - b_rong * 0.55, 0.05, z0 + b_cao * 1.05)], mau_buom)
        for j in range(6):
            zz = z0 + b_cao * j / 5
            l.khoi((b_rong * 1.05, 0.06, 0.05), (x - b_rong * 0.23, 0.08, zz), "#4f3a24")
    # Mắt thuyền ở hai bên mũi
    for sy in (-1, 1):
        s = 0.8
        w = rong / 2 * (1 - s * s) ** 0.55
        p = (s * dai / 2, sy * (w + 0.02), cao * 0.95)
        l.cau(0.2, p, mau_mat, ty_le=(1.3, 0.25, 0.8), phan=(12, 8))
        l.cau(0.09, (p[0] + 0.05, p[1] + sy * 0.04, p[2]), "#141010", ty_le=(1, 0.3, 1), phan=(10, 6))
    # Mái chèo
    for sy in (-1, 1):
        for j in range(so_mai_cheo):
            x = dai * (-0.3 + 0.55 * j / max(1, so_mai_cheo - 1))
            w = rong / 2 * (1 - (x / (dai / 2)) ** 2) ** 0.55
            l.tru(0.035, 0.035, 2.6, (x, sy * w, cao * 0.85), "#5c4229", canh=5,
                  xoay=(sy * math.radians(115), 0, 0))
    return l.tao(ten, vi_tri, huong)


# ---------------- Người (hình nộm có trang phục) ----------------

def nguoi(ten, mau_ao="#7a2e24", mau_quan="#2a2420", mau_da="#e6c29a", dau="khan_van",
          mau_khan="#2b2420", cam="", vi_tri=(0, 0, 0), huong=0.0, ty_le=1.0):
    """Người hình nộm có trang phục: áo dài qua gối, quần, đầu đội khăn vấn hoặc nón dấu.
    dau: khan_van | non_dau | toc ; cam: '' | giao (giáo) | co (cờ lệnh).
    Trả về dict {goc, than, dau, tay: {trai, phai}} để làm chuyển động."""
    goc = bpy.data.objects.new(f"{ten}_goc", None)
    goc.location = vi_tri
    goc.rotation_euler.z = huong
    goc.scale = (ty_le,) * 3
    bpy.context.scene.collection.objects.link(goc)

    l = Luoi()
    for sx in (-1, 1):  # chân
        l.tru(0.075, 0.07, 0.62, (sx * 0.1, 0, 0), mau_quan, canh=8)
    l.tru(0.31, 0.2, 0.95, (0, 0, 0.42), mau_ao, canh=14)          # áo dài qua gối
    l.khoi((0.09, 0.02, 0.6), (0.06, -0.205, 0.8), _dam(mau_ao))   # nẹp vạt áo
    l.tru(0.07, 0.07, 0.1, (0, 0, 1.36), mau_da, canh=8)            # cổ
    than = l.tao(f"{ten}_than", (0, 0, 0), cha=goc, muot=True)

    l = Luoi()
    l.cau(0.2, (0, 0, 0), mau_da, ty_le=(0.95, 0.95, 1.12), phan=(20, 14))
    for sx in (-1, 1):
        l.cau(0.027, (sx * 0.07, -0.18, 0.02), "#141010", phan=(8, 6))
        l.khoi((0.07, 0.01, 0.012), (sx * 0.075, -0.185, 0.07), "#2b2018")
    if dau == "non_dau":
        l.tru(0.34, 0.0, 0.2, (0, 0, 0.1), "#3a2a1c", canh=20)
        l.tru(0.025, 0.0, 0.14, (0, 0, 0.28), "#c9a24a", canh=6)
    elif dau == "khan_van":
        l.tru(0.215, 0.2, 0.13, (0, 0.01, 0.07), mau_khan, canh=16, xoay=(math.radians(-8), 0, 0))
        l.cau(0.19, (0, 0.03, 0.13), mau_khan, ty_le=(1, 1, 0.55), phan=(14, 8))
    else:
        l.cau(0.205, (0, 0.03, 0.06), "#1d1611", ty_le=(1, 1, 0.9), phan=(14, 10))
    dau_ob = l.tao(f"{ten}_dau", (0, 0, 1.62), cha=than, muot=True)

    tay = {}
    for sx, phia in ((-1, "trai"), (1, "phai")):
        l = Luoi()
        l.tru(0.075, 0.065, 0.6, (0, 0, -0.6), mau_ao, canh=8)
        l.cau(0.055, (0, 0, -0.64), mau_da, phan=(8, 6))
        if phia == "phai" and cam == "giao":
            l.tru(0.02, 0.02, 2.6, (0, -0.02, -1.6), "#5c4229", canh=5)
            l.tru(0.045, 0.0, 0.3, (0, -0.02, 1.0), "#b8b8b0", canh=5)
        elif phia == "phai" and cam == "co":
            l.tru(0.02, 0.02, 1.6, (0, -0.02, -1.0), "#5c4229", canh=5)
            l.mat([(0, -0.02, 0.6), (0.55, -0.02, 0.45), (0, -0.02, 0.25)], "#a8322a")
        tay[phia] = l.tao(f"{ten}_tay_{phia}", (sx * 0.29, 0, 1.3), cha=than, muot=True)
    return {"goc": goc, "than": than, "dau": dau_ob, "tay": tay, "nom": True}


def _dam(hex_mau, k=0.7):
    h = hex_mau.lstrip("#")
    return "#" + "".join(f"{int(int(h[i:i + 2], 16) * k):02x}" for i in (0, 2, 4))
