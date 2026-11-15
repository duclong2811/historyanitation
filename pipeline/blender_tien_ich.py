"""Hàm dựng hình dùng trong Blender: vật liệu toon, khối hộp, khối trụ, khối cầu...

Chỉ import được bên trong Blender (cần bpy). Script dựng cảnh trong canh/ dùng các hàm này.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

ENGINE = "EEVEE"  # render_blender.py đặt lại: "EEVEE" hoặc "CYCLES"
_VAT_LIEU = {}


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


def vat_lieu(hex_mau, ten=None):
    """Vật liệu toon: Eevee dùng Shader to RGB + ColorRamp 3 nấc; Cycles dùng diffuse phẳng."""
    key = (hex_mau, ENGINE)
    if key in _VAT_LIEU:
        return _VAT_LIEU[key]
    m = bpy.data.materials.new(ten or f"toon_{hex_mau.lstrip('#')}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mau = mau_rgb(hex_mau)
    if ENGINE == "EEVEE":
        diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
        diff.inputs["Color"].default_value = (1, 1, 1, 1)
        s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        e = ramp.color_ramp.elements
        e[0].position, e[0].color = 0.0, (0.42, 0.40, 0.52, 1)   # bóng: hơi tím lạnh
        e[1].position, e[1].color = 0.25, (0.78, 0.76, 0.80, 1)  # bán bóng
        e.new(0.6).color = (1, 1, 1, 1)                          # sáng
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


def tu_bmesh(ten, bm, mau, vi_tri=(0, 0, 0), xoay_z=0.0, cha=None, muot=False):
    me = bpy.data.meshes.new(ten)
    bm.to_mesh(me)
    bm.free()
    if muot:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(ten, me)
    ob.location = vi_tri
    ob.rotation_euler.z = xoay_z
    me.materials.append(vat_lieu(mau))
    bpy.context.scene.collection.objects.link(ob)
    if cha:
        ob.parent = cha
    return ob


def khoi(ten, kich_thuoc, vi_tri, mau, xoay_z=0.0, cha=None):
    """Khối hộp. kich_thuoc = (rộng x, sâu y, cao z); vi_tri là tâm đáy."""
    bm = bmesh.new()
    sx, sy, sz = kich_thuoc
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((sx, sy, sz, 1)) @ Matrix.Translation((0, 0, 0.5)))
    return tu_bmesh(ten, bm, mau, vi_tri, xoay_z, cha)


def tru(ten, r_duoi, r_tren, cao, vi_tri, mau, canh=16, cha=None, dich_z=0.5):
    """Khối trụ hoặc nón. dich_z=0.5: gốc ở đáy; dich_z=-0.5: gốc ở đỉnh (dùng cho tay treo)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=canh, radius1=r_duoi, radius2=r_tren, depth=cao,
                          matrix=Matrix.Translation((0, 0, cao * dich_z)))
    return tu_bmesh(ten, bm, mau, vi_tri, 0.0, cha, muot=True)


def cau(ten, ban_kinh, vi_tri, mau, ty_le=(1, 1, 1), cha=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=ban_kinh,
                              matrix=Matrix.Diagonal((*ty_le, 1)))
    return tu_bmesh(ten, bm, mau, vi_tri, 0.0, cha, muot=True)


def lang_tru_mai(ten, rong, sau, cao, vi_tri, mau, nho_ra=0.3, xoay_z=0.0):
    """Mái hai dốc (lăng trụ tam giác), vi_tri là tâm đáy mái."""
    bm = bmesh.new()
    x, y = rong / 2 + nho_ra, sau / 2 + nho_ra
    v = [bm.verts.new(p) for p in [(-x, -y, 0), (x, -y, 0), (0, -y, cao), (-x, y, 0), (x, y, 0), (0, y, cao)]]
    for f in [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]:
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return tu_bmesh(ten, bm, mau, vi_tri, xoay_z)


def ban_sao(ob, ten, vi_tri, ty_le=1.0, xoay_z=0.0):
    """Bản sao dùng chung lưới (instancing): 1.000 cây tre chỉ tốn bộ nhớ như 1 cây."""
    c = ob.copy()
    c.name = ten
    c.location = vi_tri
    c.scale = (ty_le, ty_le, ty_le)
    c.rotation_euler.z = xoay_z
    bpy.context.scene.collection.objects.link(c)
    return c
