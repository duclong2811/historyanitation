"""Đọc thông tin nhân vật trong file VRM (VRoid Studio xuất ra) mà không cần add-on.

File .vrm là file glTF nhị phân (.glb) có thêm phần mở rộng VRM. Blender nạp được bằng bộ nạp glTF có sẵn;
module này đọc phần mở rộng để biết:
  - xương nào là đầu, cổ, ngực, tay... (humanoid)
  - shape key nào là khẩu hình A I U E O, chớp mắt, vui, giận, buồn, ngạc nhiên (expressions)
Hỗ trợ VRM 0.x (phần mở rộng "VRM") và VRM 1.0 ("VRMC_vrm"). Chỉ dùng thư viện chuẩn của Python.
"""
import json
import struct
from pathlib import Path

# Tên biểu cảm chuẩn hóa -> tên trong VRM 1.0 / VRM 0.x
BIEU_CAM = {
    "a": ("aa", "a"), "i": ("ih", "i"), "u": ("ou", "u"), "e": ("ee", "e"), "o": ("oh", "o"),
    "chop_mat": ("blink", "blink"),
    "vui": ("happy", "joy"), "gian": ("angry", "angry"), "buon": ("sad", "sorrow"),
    "ngac_nhien": ("surprised", "surprised"), "thu_gian": ("relaxed", "fun"),
}

XUONG = ("hips", "spine", "chest", "upperChest", "neck", "head",
         "leftShoulder", "leftUpperArm", "leftLowerArm", "leftHand",
         "rightShoulder", "rightUpperArm", "rightLowerArm", "rightHand",
         "leftUpperLeg", "rightUpperLeg")


def doc_glb_json(path):
    b = Path(path).read_bytes()
    magic, _ver, _len = struct.unpack_from("<4sII", b, 0)
    if magic != b"glTF":
        raise ValueError(f"{path} không phải file glTF/VRM")
    clen, ctype = struct.unpack_from("<I4s", b, 12)
    if ctype != b"JSON":
        raise ValueError("thiếu phần JSON trong file glTF")
    return json.loads(b[20:20 + clen].decode("utf-8"))


def doc_vrm(path):
    """Trả về dict:
    {"phien_ban": "0.x"|"1.0", "huong_mat": "-Y"|"+Y" (hướng nhân vật nhìn sau khi nạp vào Blender),
     "xuong": {"head": "<tên node>", ...},
     "bieu_cam": {"a": [("<tên mesh glTF>", chỉ_số_morph, trọng_số 0..1), ...], ...}}"""
    g = doc_glb_json(path)
    nodes, meshes = g.get("nodes", []), g.get("meshes", [])
    ext = g.get("extensions", {})
    ket = {"xuong": {}, "bieu_cam": {}}

    def ten_mesh_cua_node(i):
        n = nodes[i]
        return meshes[n["mesh"]].get("name", f"mesh{n['mesh']}") if "mesh" in n else None

    if "VRMC_vrm" in ext:  # VRM 1.0: nhân vật nhìn về +Z glTF = -Y Blender
        v = ext["VRMC_vrm"]
        ket["phien_ban"], ket["huong_mat"] = "1.0", "-Y"
        for ten, x in v.get("humanoid", {}).get("humanBones", {}).items():
            if ten in XUONG:
                ket["xuong"][ten] = nodes[x["node"]].get("name", f"node{x['node']}")
        bieu = {**v.get("expressions", {}).get("preset", {}), **v.get("expressions", {}).get("custom", {})}
        for chuan, (ten1, _ten0) in BIEU_CAM.items():
            e = bieu.get(ten1)
            if e:
                ket["bieu_cam"][chuan] = [(ten_mesh_cua_node(b["node"]), b["index"], float(b.get("weight", 1.0)))
                                          for b in e.get("morphTargetBinds", []) if ten_mesh_cua_node(b["node"])]
    elif "VRM" in ext:  # VRM 0.x: nhân vật nhìn về -Z glTF = +Y Blender
        v = ext["VRM"]
        ket["phien_ban"], ket["huong_mat"] = "0.x", "+Y"
        for x in v.get("humanoid", {}).get("humanBones", []):
            if x.get("bone") in XUONG:
                ket["xuong"][x["bone"]] = nodes[x["node"]].get("name", f"node{x['node']}")
        nhom = {(gr.get("presetName") or gr.get("name", "")).lower(): gr
                for gr in v.get("blendShapeMaster", {}).get("blendShapeGroups", [])}
        for chuan, (_ten1, ten0) in BIEU_CAM.items():
            gr = nhom.get(ten0)
            if gr:
                ket["bieu_cam"][chuan] = [(meshes[b["mesh"]].get("name", f"mesh{b['mesh']}"), b["index"],
                                           float(b.get("weight", 100)) / 100.0) for b in gr.get("binds", [])]
    else:
        raise ValueError(f"{path} là glTF nhưng không có phần mở rộng VRM")
    return ket


if __name__ == "__main__":
    import sys
    print(json.dumps(doc_vrm(sys.argv[1]), ensure_ascii=False, indent=1))
