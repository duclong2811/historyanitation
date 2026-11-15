# Hoạt hình lịch sử Việt Nam bằng code

Làm phim hoạt hình hoàn toàn bằng công cụ miễn phí, chạy trên máy, không tốn API:
**Blender + Python + FFmpeg + Piper TTS**. Máy mục tiêu: GTX 1660 Super (6GB VRAM).

```
Kịch bản (YAML) ──► Giọng đọc ──► Chia shot ──► Render từng shot (Blender) ──► Ghép phim (FFmpeg)
```

## Cài đặt (một lần)

1. **Blender 4.2 trở lên**: https://www.blender.org/download/
2. **FFmpeg** có trong PATH. Trên Windows: `winget install Gyan.FFmpeg`
3. **Python 3.10+** và các gói:

```bash
pip install -r requirements.txt
```

Nếu chương trình không tự tìm thấy Blender, đặt biến môi trường `BLENDER` trỏ tới `blender.exe`.

## Chạy

Xem thử nhanh (mỗi shot một ảnh nhỏ, ra `build/mau/xem_thu.png`):

```bash
python pipeline/chay.py kich-ban/mau.yaml --xem-thu
```

Làm cả phim (ra `output/mau.mp4`):

```bash
python pipeline/chay.py kich-ban/mau.yaml
```

Lần đầu chạy, Piper tự tải giọng tiếng Việt (khoảng 60MB). Sửa kịch bản rồi chạy lại thì chỉ những shot thay đổi mới được render lại.

## Các bước

| Bước | File | Việc |
|---|---|---|
| 1. Kịch bản | `kich-ban/*.yaml` | Nhân vật, cảnh, lời thoại, camera, động tác. Xem chú thích trong `kich-ban/mau.yaml` |
| 2. Giọng đọc | `pipeline/giong_doc.py` | Piper đọc offline; VietTTS (giọng tự nhiên, mỗi nhân vật một giọng, xem `docs/giong-viettts.md`); hoặc file tự thu trong `giong/<tên kịch bản>/s01.wav`... |
| 3. Chia shot | `pipeline/chia_shot.py` | Mỗi lời thoại một shot, thời lượng theo giọng đọc -> `build/<tên>/shots.json` |
| 4. Render | `pipeline/render_blender.py` | Dựng cảnh, đặt nhân vật, camera đẩy chậm, shader toon, nét viền Freestyle, render on twos |
| 5. Ghép phim | `pipeline/ghep_phim.py` | Phóng lên 1080p, ghép tiếng, phụ đề, nhạc nền, mã hóa NVENC |

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `kich-ban/` | Kịch bản YAML |
| `canh/` | Script Python dựng cảnh (mỗi cảnh một file, có hàm `dung(t)`) |
| `pipeline/` | Các bước của pipeline; `blender_tien_ich.py` là bộ hàm dựng hình và vật liệu toon |
| `assets/nhan_vat/` | Mô hình nhân vật `.glb`/`.fbx` (từ VRoid, qua Mixamo) |
| `assets/dong_tac/` | Động tác Mixamo `.fbx`, gọi bằng tên file trong `hanh_dong` |
| `giong/` | Giọng tự thu (khi `giong.cach: tu_thu`) |
| `docs/` | Ghi chú về hướng làm, nguồn tài nguyên, tối ưu, từ khóa tìm hiểu |
| `build/`, `output/` | Đầu ra, không commit |

## Kịch bản có sẵn

| Kịch bản | Nội dung |
|---|---|
| `kich-ban/mau.yaml` | Mẫu ngắn để thử pipeline |
| `kich-ban/gia_dinh_1788.yaml` | Nguyễn Ánh lấy lại Gia Định (1788). Tư liệu: `docs/boi-canh/gia-dinh-1788.md` |

Xem thử vài shot cho nhanh:

```bash
python pipeline/chay.py kich-ban/gia_dinh_1788.yaml --xem-thu --chi s03,s04
```

Tùy chọn nhân vật trong kịch bản (khi chưa có mô hình thật):
- `an_hinh: true`: chỉ có giọng (người kể), không hiện hình.
- `dau`: `khan_van` | `non_dau` | `toc`. `cam`: `giao` | `co`. `mau`, `mau_quan`, `mau_khan`: màu áo, quần, khăn.

Camera của shot là `rong` | `trung` | `can` (đặt theo người nói), hoặc tên một camera đặt sẵn trong script cảnh.

## Nhân vật thật thay cho hình nộm

Chưa khai báo `mo_hinh` thì pipeline dùng hình nộm tạm để thử bố cục. Để dùng nhân vật thật:

1. Tạo nhân vật trong **VRoid Studio**, xuất **VRM**.
2. Mở bằng Blender có **VRM Add-on for Blender**, xuất ra **FBX**.
3. Tải FBX lên **Mixamo** để tự gắn xương, rồi tải về bản T-pose **With Skin** -> `assets/nhan_vat/<tên>.fbx`.
4. Tải các động tác (vẫy tay, đi bộ, nói chuyện...) bản **Without Skin** -> `assets/dong_tac/<tên động tác>.fbx`.
5. Trong kịch bản: `mo_hinh: assets/nhan_vat/<tên>.fbx` và `hanh_dong: <tên động tác>`.

Vì nhân vật và động tác cùng đi qua Mixamo nên tên xương khớp nhau, động tác gắn thẳng vào được.

## Cảnh mới

Chép `canh/san_mau.py` hoặc `canh/gia_dinh_1788.py` thành file mới rồi khai báo trong mục `canh` của kịch bản. Các hàm dựng sẵn trong `pipeline/blender_tien_ich.py`:

- Khối cơ bản: `khoi`, `tru`, `cau`, `lang_tru_mai`, `ban_sao` (nhân bản dùng chung lưới), `Luoi` (ghép nhiều khối nhiều màu thành một object).
- Trời: `hdri` (tự tải bầu trời từ Poly Haven), `mat_troi`, `den_vien`, `suong`.
- Cây: `dua_nuoc`, `cay_dua`, `bui_co`.
- Công trình: `nha_la`, `choi_canh`, `coc_rao`, `hang_rao`, `co` (cờ bay).
- Thuyền: `thuyen` (thân cong, mui, buồm cói, mắt thuyền, mái chèo), `dap_dinh` (bập bềnh).
- Người: `nguoi` (áo, quần, khăn vấn hoặc nón dấu, giáo hoặc cờ).

Hàm `dung(t)` của cảnh có thể trả về vị trí đứng của nhân vật (`cho_dung`, gắn được lên thuyền) và các camera đặt sẵn (`camera`). Xem ví dụ trong `canh/gia_dinh_1788.py`.

## Chia việc

- **Trên cloud (Claude)**: viết code dựng mô hình khó, cảnh, shader; render ảnh xem thử bằng CPU; đẩy lên repo.
- **Trên máy bạn**: `git pull`, render bản chính thức bằng GPU.
