# Chế độ lai: nền AI + nhân vật VRoid 3D

```
Nền: ComfyUI vẽ mỗi cảnh 1 ảnh  ─┐
                                 ├─► ghép lớp ─► phim
Nhân vật: VRoid render 3D (Blender) ─┘
```

- **Nền** chi tiết kiểu anime, vẽ **một lần cho mỗi cảnh**, các shot cùng cảnh dùng chung. Camera chuyển động 2.5D như
  chế độ ảnh AI.
- **Nhân vật** giống hệt nhau ở mọi shot, **nhép miệng theo giọng**, chớp mắt, thở, đổi **biểu cảm** theo kịch bản,
  làm **động tác** (giơ tay, vẫy tay, chỉ tay, gật đầu). Shader toon và nét viền chạy trên GPU nên nhanh.
- **Không cần add-on VRM**: pipeline tự đọc file `.vrm`.

Ví dụ: `kich-ban/gia_dinh_1788_lai.yaml`.

## 1. Tạo nhân vật trong VRoid Studio

1. Tải **VRoid Studio** (miễn phí): trên Steam, hoặc https://vroid.com/en/studio
2. **New** → chọn nam hoặc nữ, chỉnh **Face**, **Hair**, **Body**, **Outfit** bằng thanh trượt.
3. **Trang phục Việt cổ**: VRoid không có sẵn. Cách làm:
   - Chọn áo dài tay, dài qua gối (Outfit → Tops → One-piece), chỉnh màu trong **Edit Texture** (ví dụ đỏ sẫm cho
     Nguyễn Ánh).
   - **Khăn vấn**: dùng **Hair → Hairstyle Editor**, vẽ một lớp tóc quấn quanh đầu rồi đổi màu đen như vải.
   - Nón dấu, giáo, kiếm: chưa có. Bước sau mình sẽ cho gắn đồ vật 3D vào tay hoặc đầu nhân vật.
4. **Export** (biểu tượng chia sẻ) → **Export as VRM**. Chọn VRM 1.0 hoặc 0.x đều được. Điền tên, bấm Export.
5. Lưu file vào `assets/nhan_vat/` trong repo, ví dụ `assets/nhan_vat/nguyen_anh.vrm`.

## 2. Kịch bản

```yaml
che_do: lai

nhan_vat:
  nguoi_ke:
    an_hinh: true                          # chỉ có giọng
  nguyen_anh:
    mo_hinh: assets/nhan_vat/nguyen_anh.vrm

canh:                                      # mỗi cảnh 1 ảnh nền (không có người)
  boong_thuyen:
    ve: "deck of a wooden war junk at sunrise, battened sails, river, nipa palms"

loi:
  - nhan_vat: nguyen_anh
    canh: boong_thuyen
    noi: "Các tướng sĩ! Hôm nay ta lấy lại đất Gia Định."
    camera: trung          # can (mặt) | trung (nửa người) | rong (toàn thân)
    hanh_dong: gio_cao     # dung_yen | gio_cao | vay_tay | chi_tay | gat_dau
    cam_xuc: gian          # vui | gian | buon | ngac_nhien | thu_gian (bỏ trống: bình thường)
    vi_tri: 0.45           # vị trí ngang trong khung, 0 = trái, 1 = phải
    goc_quay: 12           # camera lệch sang bên bao nhiêu độ
    chuyen_dong: dung_yen  # chuyển động của nền (như chế độ ảnh AI)
```

## 3. Chạy

ComfyUI phải đang mở (`run_nvidia_gpu.bat`). Xem thử (nền + một ảnh nhân vật mỗi shot):

```powershell
python pipeline/chay.py kich-ban/gia_dinh_1788_lai.yaml --xem-thu
```

Làm cả phim:

```powershell
python pipeline/chay.py kich-ban/gia_dinh_1788_lai.yaml
```

Sửa lời thoại thì chỉ shot đó được render lại nhân vật, nền giữ nguyên.

## Giới hạn hiện tại

- **Mỗi shot một nhân vật.** Hội thoại hai người thì cắt qua lại giữa hai shot (cách phim hoạt hình hay làm).
- **Toàn thân (`rong`)** chưa có bóng đổ dưới chân. Nên dùng `can` và `trung` cho shot thoại.
- **Ánh sáng nhân vật** chỉ được pha theo tông màu nền, chưa khớp hướng nắng trong ảnh nền.
- **Động tác** có 5 kiểu dựng sẵn. Động tác Mixamo (đi, chạy, đánh kiếm...) sẽ thêm sau.
