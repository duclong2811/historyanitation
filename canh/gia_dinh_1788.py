"""Cảnh: sông Bến Nghé lúc bình minh năm 1788. Đoàn thuyền chiến của Nguyễn Ánh ngược sông
tiến về Gia Định; trên bờ là đồn lũy đất, rào cọc, chòi canh của quân Tây Sơn, nhà lá, dừa nước.

Bố cục: sông chạy dọc trục X, mặt nước ở z = 0. Bờ có đồn lũy ở phía +Y (từ y = 29).
Thuyền đi về phía +X. Xem tư liệu: docs/boi-canh/gia-dinh-1788.md
"""
import math
import random

# ⚠ Màu cờ và áo lính của hai phe chưa có nguồn chắc chắn, chỉnh ở đây khi có tư liệu.
MAU_CO_NGUYEN = "#e9e2cf"
MAU_CO_TAY_SON = "#a8322a"
MAU_AO_LINH_NGUYEN = "#3c4f6b"
MAU_AO_LINH_TAY_SON = "#7a2e24"

BO = 29.0       # mép bờ có đồn lũy
CAO_BO = 0.6    # bờ cao hơn mặt nước


def dung(t):
    rnd = random.Random(1788)

    # ---- Trời, nắng, sương ----
    t.hdri("qwantani_sunrise_puresky", do_sang=0.45, xoay_do=200)
    t.mat_troi(cao_do=14, huong_do=150, mau="#ffc58f", manh=3.8)
    t.den_vien(cao_do=10, huong_do=-40, mau="#ffd6a0", manh=1.6)
    t.suong(mat_do=0.0025, mau="#f3d9bd")

    # ---- Sông và hai bờ ----
    t.khoi("song", (600, 400, 0.1), (0, 0, -0.1), "#6e8c90")
    t.khoi("bo_don", (600, 200, CAO_BO + 0.5), (0, BO + 100, -0.5), "#8f7a52")
    t.khoi("bo_xa", (600, 60, 0.9), (0, -120, -0.5), "#7d7a50")

    # ---- Lũy đất và rào cọc ----
    x0, x1 = -40.0, 70.0
    cong_x = (8.0, 13.0)  # cổng đồn
    y_luy = BO + 4.0
    l = t.Luoi()
    for a, b in ((x0, cong_x[0]), (cong_x[1], x1)):
        mc = lambda x: [(x, y_luy - 2.6, CAO_BO), (x, y_luy - 0.8, CAO_BO + 1.6),
                        (x, y_luy + 0.8, CAO_BO + 1.6), (x, y_luy + 2.6, CAO_BO)]
        l.dai([mc(a), mc(b)], "#7c6440", dong_dau=True, dong_cuoi=True)
    l.tao("luy_dat")
    coc = t.coc_rao("coc_mau", cao=2.3, mau="#6f5333")
    coc.location.z = -100  # cọc mẫu giấu dưới đất
    z_rao = CAO_BO + 1.55
    t.hang_rao(coc, (x0, y_luy, z_rao), (cong_x[0], y_luy, z_rao), khoang=0.24, ten="rao_a")
    t.hang_rao(coc, (cong_x[1], y_luy, z_rao), (x1, y_luy, z_rao), khoang=0.24, ten="rao_b")
    # Cổng: hai cột và xà ngang, cánh cổng gỗ
    l = t.Luoi()
    for x in cong_x:
        l.tru(0.22, 0.2, 5.0, (x, y_luy, CAO_BO), "#5e4429", canh=8)
    l.khoi((cong_x[1] - cong_x[0] + 0.8, 0.4, 0.4), ((cong_x[0] + cong_x[1]) / 2, y_luy, CAO_BO + 4.4), "#5e4429")
    l.khoi((2.3, 0.15, 3.4), (cong_x[0] + 1.3, y_luy - 0.1, CAO_BO), "#6b4f31", xoay=(0, 0, 0.5))
    l.khoi((2.3, 0.15, 3.4), (cong_x[1] - 1.3, y_luy - 0.1, CAO_BO), "#6b4f31", xoay=(0, 0, -0.5))
    l.tao("cong_don")

    # Chòi canh
    t.choi_canh("choi_canh_1", (20.0, y_luy + 3.5, CAO_BO), cao=5.0)
    t.choi_canh("choi_canh_2", (-14.0, y_luy + 3.5, CAO_BO), cao=4.6)
    # Cờ trên lũy
    for i, x in enumerate([-30, -6, 6, 15, 30, 52]):
        t.co(f"co_ts_{i}", (x, y_luy + 0.6, CAO_BO + 1.5), mau=MAU_CO_TAY_SON, cao=4.5)

    # Bến gỗ
    l = t.Luoi()
    l.khoi((2.2, 7.0, 0.15), (32.0, BO - 2.5, CAO_BO), "#7a5f40")
    for y in (BO - 5.5, BO - 3.0, BO - 0.5):
        for x in (31.1, 32.9):
            l.tru(0.09, 0.09, 1.6, (x, y, -0.9), "#5a4128", canh=6)
    l.tao("ben_go")

    # Nhà lá trong đồn
    for i, (x, y, h) in enumerate([(-24, 44, 0.3), (-4, 47, 0.2), (4, 42, -0.2), (28, 45, 0.4),
                                   (40, 41, 0.1), (-34, 40, -0.3), (16, 52, 0.0)]):
        t.nha_la(f"nha_{i}", rnd.uniform(4.5, 6.5), rnd.uniform(3.5, 4.5), 2.2, (x, y, CAO_BO), huong=h,
                 nha_san=0.6 if i % 3 == 0 else 0.0)

    # ---- Cây ven sông ----
    dn = t.dua_nuoc("dua_nuoc_mau")
    dn.location.z = -100
    for i in range(140):  # dừa nước dọc mép bờ đồn
        x = rnd.uniform(-90, 120)
        if 28 < x < 36:
            continue  # chừa chỗ bến
        t.ban_sao(dn, f"dn_{i}", (x, BO + rnd.uniform(-1.8, 1.2), 0.0), rnd.uniform(0.8, 1.3), rnd.uniform(0, 6.3))
    for i in range(200):  # dừa nước bờ xa
        t.ban_sao(dn, f"dnx_{i}", (rnd.uniform(-160, 200), rnd.uniform(-93, -88), 0.4),
                  rnd.uniform(1.0, 1.6), rnd.uniform(0, 6.3))
    co_mau = t.bui_co("co_mau")
    co_mau.location.z = -100
    for i in range(120):
        t.ban_sao(co_mau, f"co_{i}", (rnd.uniform(-60, 90), rnd.uniform(BO + 0.5, BO + 2.5), CAO_BO),
                  rnd.uniform(0.8, 1.4), rnd.uniform(0, 6.3))
    dua = [t.cay_dua(f"dua_mau_{k}", cao=rnd.uniform(7, 10), seed=k) for k in range(3)]
    for d in dua:
        d.location.z = -100
    for i in range(70):  # rặng dừa sau đồn
        x, y = rnd.uniform(-70, 100), rnd.uniform(BO + 9, BO + 45)
        if abs(x - 20) < 4 and y < BO + 12:
            continue
        t.ban_sao(dua[i % 3], f"dua_{i}", (x, y, CAO_BO), rnd.uniform(0.8, 1.2), rnd.uniform(0, 6.3))
    for i in range(60):  # dừa bờ xa
        t.ban_sao(dua[i % 3], f"duax_{i}", (rnd.uniform(-160, 200), rnd.uniform(-110, -95), 0.4),
                  rnd.uniform(0.9, 1.3), rnd.uniform(0, 6.3))

    # ---- Lính Tây Sơn trên đồn ----
    for i, x in enumerate([cong_x[0] - 1.5, cong_x[1] + 1.5, -8, 36]):
        t.nguoi(f"linh_ts_{i}", mau_ao=MAU_AO_LINH_TAY_SON, dau="non_dau", cam="giao",
                vi_tri=(x, y_luy + 1.4, CAO_BO + (0 if i < 2 else 1.6)), huong=rnd.uniform(-0.3, 0.3))

    # ---- Đoàn thuyền chiến của Nguyễn Ánh ----
    doan = [("thuyen_chu", (0, 0), 14.0), ("thuyen_1", (-18, 7), 11.0), ("thuyen_2", (-15, -9), 11.5),
            ("thuyen_3", (-34, 1), 10.5), ("thuyen_4", (-31, 13), 10.0), ("thuyen_5", (-48, -6), 10.0),
            ("thuyen_6", (11, 10), 10.5)]
    for k, (ten, (x, y), dai) in enumerate(doan):
        th = t.thuyen(ten, (x, y, 0.0), huong=rnd.uniform(-0.06, 0.06) + 0.12, dai=dai, rong=dai * 0.2,
                      so_buom=2 if dai > 10.6 else 1)
        th_co = t.co(f"{ten}_co", (-dai * 0.42, 0, 1.2), mau=MAU_CO_NGUYEN, cao=3.6, rong=1.3, dai=0.9)
        th_co.parent = th
        if ten != "thuyen_chu":
            for j in range(4):  # lính trên thuyền
                p = t.nguoi(f"{ten}_linh_{j}", mau_ao=MAU_AO_LINH_NGUYEN, dau="non_dau",
                            cam="giao" if j % 2 == 0 else "", vi_tri=(dai * (0.3 - 0.13 * j), (j % 2 - 0.5) * 0.9, 0.8),
                            huong=math.radians(90 + rnd.uniform(-20, 20)), ty_le=0.95)
                p["goc"].parent = th
        t.dap_dinh(th, bien_do=0.035, nhip=0.45, pha=k * 1.7)
    # Lính cận vệ trên thuyền chủ
    th = t.bpy.data.objects["thuyen_chu"]
    for j, (x, y) in enumerate([(2.5, -0.8), (2.5, 0.8), (-4.2, 0.6)]):
        p = t.nguoi(f"can_ve_{j}", mau_ao=MAU_AO_LINH_NGUYEN, dau="non_dau", cam="giao" if j < 2 else "co",
                    vi_tri=(x, y, 0.82), huong=math.radians(100))
        p["goc"].parent = th

    return {
        "cho_dung": {
            "nguyen_anh": {"vi_tri": (3.9, 0.0, 0.92), "huong": 150, "cha": "thuyen_chu"},
            "linh_tay_son": {"vi_tri": (20.0, y_luy + 3.5, CAO_BO + 5.15), "huong": 10},
        },
        "camera": {
            "toan_canh": {"vi_tri": (-21, -17, 2.8), "nhin": (4, 16, 4.5), "tieu_cu": 24, "day": (2, 1.5, -0.2)},
            "doan_thuyen": {"vi_tri": (-9, -15, 1.4), "nhin": (4, 6, 3.0), "tieu_cu": 30, "day": (1.5, 1.8, 0)},
            "don_luy": {"vi_tri": (25, 13, 1.4), "nhin": (16, 33, 3.6), "tieu_cu": 30, "day": (-0.5, 2.5, 0)},
            "choi_canh": {"vi_tri": (21.6, y_luy - 1.6, CAO_BO + 6.45), "nhin": (20.0, y_luy + 3.5, CAO_BO + 6.7),
                          "tieu_cu": 50, "day": (-0.15, 0.5, 0.0)},
        },
    }
