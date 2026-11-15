"""Cảnh mẫu: sân đất, túp lều, rặng tre, đồi xa.

Mỗi script cảnh cần có hàm dung(t), với t là module pipeline/blender_tien_ich.py.
Quy ước: nhân vật đứng quanh gốc tọa độ, nhìn về phía -Y (về phía camera); hậu cảnh ở phía +Y.
"""
import math
import random


def dung(t):
    random.seed(7)  # cảnh giống hệt nhau ở mọi shot

    # Sân đất
    t.khoi("san", (60, 60, 0.1), (0, 10, -0.1), "#b89a6a")

    # Túp lều: tường, cửa, mái
    t.khoi("lieu_tuong", (3.2, 2.4, 1.8), (-3.2, 4.5, 0), "#c9a46c")
    t.khoi("lieu_cua", (0.8, 0.05, 1.3), (-3.2, 3.29, 0), "#5a3d24")
    t.lang_tru_mai("lieu_mai", 3.2, 2.4, 1.4, (-3.2, 4.5, 1.8), "#7a6a3a", nho_ra=0.45)

    # Rặng tre: một cây mẫu, các cây khác là bản sao dùng chung lưới
    than = t.tru("tre_mau", 0.07, 0.05, 7.0, (6, 7, 0), "#6f9a3c", canh=8)
    la = t.cau("tre_la_mau", 0.9, (0, 0, 6.6), "#4f7a2a", ty_le=(1, 1, 1.6), cha=than)
    for i in range(70):
        x = random.uniform(1.5, 14)
        y = random.uniform(5.5, 12)
        k = random.uniform(0.7, 1.25)
        c = t.ban_sao(than, f"tre_{i}", (x, y, 0), k, random.uniform(0, math.tau))
        c.rotation_euler.x = random.uniform(-0.08, 0.08)
        l2 = t.ban_sao(la, f"tre_la_{i}", (0, 0, 6.6))
        l2.parent = c

    # Đống rơm
    for i, (x, y) in enumerate([(-6.0, 3.0), (-7.2, 5.2)]):
        t.tru(f"rom_{i}", 0.9, 0.05, 1.8, (x, y, 0), "#d8b45a", canh=16)

    # Đồi xa
    for i, (x, y, r) in enumerate([(-14, 32, 10), (2, 38, 14), (18, 34, 11)]):
        t.cau(f"doi_{i}", r, (x, y, -r * 0.55), "#7d9a6a", ty_le=(1.4, 0.6, 1))
