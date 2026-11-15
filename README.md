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
| 2. Giọng đọc | `pipeline/giong_doc.py` | Piper đọc offline, hoặc dùng file tự thu trong `giong/<tên kịch bản>/s01.wav`... |
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

## Nhân vật thật thay cho hình nộm

Chưa khai báo `mo_hinh` thì pipeline dùng hình nộm tạm để thử bố cục. Để dùng nhân vật thật:

1. Tạo nhân vật trong **VRoid Studio**, xuất **VRM**.
2. Mở bằng Blender có **VRM Add-on for Blender**, xuất ra **FBX**.
3. Tải FBX lên **Mixamo** để tự gắn xương, rồi tải về bản T-pose **With Skin** -> `assets/nhan_vat/<tên>.fbx`.
4. Tải các động tác (vẫy tay, đi bộ, nói chuyện...) bản **Without Skin** -> `assets/dong_tac/<tên động tác>.fbx`.
5. Trong kịch bản: `mo_hinh: assets/nhan_vat/<tên>.fbx` và `hanh_dong: <tên động tác>`.

Vì nhân vật và động tác cùng đi qua Mixamo nên tên xương khớp nhau, động tác gắn thẳng vào được.

## Cảnh mới

Chép `canh/san_mau.py` thành file mới, dùng các hàm trong `pipeline/blender_tien_ich.py` (`khoi`, `tru`, `cau`, `lang_tru_mai`, `ban_sao`) để dựng, rồi khai báo trong mục `canh` của kịch bản.

## Chia việc

- **Trên cloud (Claude)**: viết code dựng mô hình khó, cảnh, shader; render ảnh xem thử bằng CPU; đẩy lên repo.
- **Trên máy bạn**: `git pull`, render bản chính thức bằng GPU.
