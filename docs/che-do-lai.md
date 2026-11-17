# Chế độ lai: nền AI + nhân vật VRoid 3D

```
Nền: ComfyUI vẽ mỗi cảnh 1 ảnh  ─┐
                                 ├─► ghép lớp ─► phim
Nhân vật: VRoid render 3D (Blender) ─┘
```

- **Nền** chi tiết kiểu anime, vẽ **một lần cho mỗi cảnh**, các shot cùng cảnh dùng chung. Camera chuyển động 2.5D như
  chế độ ảnh AI.
- **Nhân vật** giống hệt nhau ở mọi shot, **nhép miệng theo giọng**, chớp mắt, thở, đổi **biểu cảm** theo kịch bản,
  làm **động tác** dựng sẵn hoặc **động tác Mixamo** bất kỳ. Shader toon và nét viền chạy trên GPU nên nhanh.
- **Camera** đẩy vào, kéo ra, lia: nền và nhân vật cùng chuyển động, có chiều sâu.
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

## 3. Động tác Mixamo (đi, chạy, đánh kiếm, chào...)

Ngoài 5 động tác dựng sẵn, `hanh_dong` dùng được **mọi động tác trên Mixamo** (miễn phí, cần tài khoản Adobe).
**Không cần** đưa nhân vật VRoid lên Mixamo: tải động tác của nhân vật mặc định, pipeline tự chép sang
nhân vật của bạn theo tên xương.

1. Vào https://www.mixamo.com, đăng nhập, chọn tab **Animations**.
2. Tìm động tác (ví dụ `Pointing`, `Waving`, `Sword Slash`, `Talking`, `Walking`). Động tác đi hoặc chạy thì
   tick **In Place** để nhân vật đi tại chỗ.
3. Bấm **Download**: Format **FBX Binary (.fbx)**, Skin **Without Skin**, Frames per Second **30**.
4. Lưu vào `assets/dong_tac/` với tên ngắn không dấu, ví dụ `assets/dong_tac/chi_huy.fbx`.
5. Trong kịch bản: `hanh_dong: chi_huy`. Shot dài hơn động tác thì động tác tự lặp lại.

Thứ tự ưu tiên: có file `assets/dong_tac/<hanh_dong>.fbx` thì dùng Mixamo, không có thì dùng động tác dựng sẵn
cùng tên (`gio_cao`, `vay_tay`, `chi_tay`, `gat_dau`, `dung_yen`).

Lưu ý bản quyền: động tác Mixamo dùng trong phim (kể cả thương mại) được, nhưng không được phát tán lại file
gốc. Giữ repo ở chế độ **Private** nếu đưa file `.fbx` vào repo.

## 4. Camera

`chuyen_dong` (day_vao, keo_ra, lia_trai...) giờ di chuyển **cả nền lẫn nhân vật**: nhân vật ở gần camera hơn
nên phóng to và trôi mạnh hơn nền một chút, tạo chiều sâu. Ví dụ đẩy chậm vào nhân vật đang nói:

```yaml
    camera: trung
    chuyen_dong: day_vao
```

## 5. Chạy

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
- **Động tác Mixamo** được chép theo hướng xương nên không giữ được độ vặn cổ tay. Ngón tay chưa cử động.
