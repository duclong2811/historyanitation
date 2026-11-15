# Chế độ ảnh AI (anime)

Mỗi shot có một **prompt**. **ComfyUI** chạy trên máy bạn vẽ ra một ảnh anime chi tiết, pipeline cho
**camera chuyển động** (đẩy, kéo, lia) kèm **parallax 2.5D** theo độ sâu ảnh, rồi ghép giọng và phụ đề như
chế độ Blender. Miễn phí, không cần API, chạy được trên GTX 1660 Super.

```
Kịch bản (prompt từng shot) ──► ComfyUI vẽ ảnh ──► Chuyển động 2.5D ──► Ghép giọng, phụ đề ──► Phim
```

Ví dụ: `kich-ban/gia_dinh_1788_anime.yaml`.

## Cài đặt (một lần)

### 1. ComfyUI

1. Vào https://github.com/comfyanonymous/ComfyUI/releases, tải bản **Windows portable cho NVIDIA**
   (file `ComfyUI_windows_portable_nvidia.7z`).
2. Giải nén bằng 7-Zip vào một thư mục **ngoài** repo này, ví dụ `C:\ComfyUI_windows_portable`.
3. Chạy `run_nvidia_gpu.bat`. Trình duyệt mở ra `http://127.0.0.1:8188` là được. **Để cửa sổ này chạy**
   trong lúc làm phim.

### 2. Model anime

Tải **Animagine XL 4.0** (khoảng 7GB):
https://huggingface.co/cagliostrolab/animagine-xl-4.0/resolve/main/animagine-xl-4.0-opt.safetensors

Đặt vào `C:\ComfyUI_windows_portable\ComfyUI\models\checkpoints\`. Giấy phép: OpenRAIL++
(dùng ảnh thương mại được, nhưng có danh sách điều cấm, nên đọc trên trang model).

### 3. Thư viện cho pipeline

```powershell
pip install -r requirements.txt
```

Parallax 2.5D (vật gần trôi nhanh hơn vật xa) cần thêm torch và transformers. Bản CPU là đủ, khoảng 200MB:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

```powershell
pip install transformers
```

Không cài cũng chạy được, chỉ là không có parallax.

## Làm phim

Vẽ ảnh và xem trước (ra `build\gia_dinh_1788_anime\xem_thu.png`):

```powershell
python pipeline/chay.py kich-ban/gia_dinh_1788_anime.yaml --xem-thu
```

Ảnh nào chưa ưng thì sửa `ve` trong kịch bản rồi chạy lại (chỉ shot đã sửa được vẽ lại), hoặc thử hạt
giống khác:

```powershell
python pipeline/chay.py kich-ban/gia_dinh_1788_anime.yaml --xem-thu --ve-lai s03
```

Ưng hết thì làm cả phim (ra `output\gia_dinh_1788_anime.mp4`):

```powershell
python pipeline/chay.py kich-ban/gia_dinh_1788_anime.yaml
```

## Viết prompt

- Viết bằng **tiếng Anh**, kiểu liệt kê từ khóa cách nhau bằng dấu phẩy.
- Thứ tự prompt cuối cùng: **mô tả nhân vật** (mục `nhan_vat.<tên>.mo_ta`, tự chèn khi nhân vật có trên
  hình) → **mô tả shot** (`ve`) → **phong cách chung** (`anh_ai.phong_cach`).
- Cảnh không có người: bắt đầu bằng `no humans, scenery`.
- Một nhân vật: `solo`, kèm khung hình như `upper body`, `full body`, `close-up`, góc máy như `from below`,
  `from side`.
- **Đồ Việt cổ**: model hay vẽ nhầm sang Trung Quốc hoặc Nhật. Mô tả cụ thể (khăn vấn: `dark wrapped
  turban`; nón dấu: `wide conical hat with a metal spike`; dừa nước: `nipa palms`) và chặn trong
  `phong_cach_am` (`chinese architecture, pagoda, samurai, kimono, hanfu, queue hairstyle`...).
- `chuyen_dong` nên hợp với ảnh: cảnh rộng dùng `day_vao` hoặc `keo_ra`; ảnh ngang có nhiều thứ dùng `lia_trai` hoặc
  `lia_phai`; cận mặt dùng `day_vao` với `tieu_diem` đặt vào mặt.

## Giới hạn cần biết

- **Nhân vật giữa các shot chưa giống hệt nhau.** Cùng mô tả thì quần áo, màu sắc gần giống, nhưng khuôn
  mặt có thể khác. Bước nâng cấp sau: IP-Adapter (dùng ảnh mẫu nhân vật) hoặc tự huấn luyện LoRA cho từng
  nhân vật.
- **Nhân vật chưa nhép miệng.** Ảnh là tĩnh, chỉ có camera chuyển động.
- **Độ chính xác lịch sử**: AI không biết rõ trang phục và kiến trúc Việt thế kỷ 18. Luôn soát ảnh với tư liệu.

## Xử lý lỗi

| Lỗi | Cách sửa |
|---|---|
| `Không kết nối được ComfyUI` | Chưa mở `run_nvidia_gpu.bat`, hoặc ComfyUI chạy ở cổng khác (sửa `anh_ai.may_chu`) |
| `ComfyUI không thấy model` | Tên file trong `anh_ai.mo_hinh` phải khớp đúng tên file trong `models\checkpoints` |
| Ảnh đen hoặc toàn nhiễu | Dòng GTX 16xx đôi khi lỗi với fp16. Sửa `run_nvidia_gpu.bat`, thêm `--force-fp32` vào cuối dòng lệnh |
| Hết VRAM (out of memory) | Thêm `--lowvram` vào cuối dòng lệnh trong `run_nvidia_gpu.bat` |

## Workflow riêng (nâng cao)

Muốn thêm LoRA, upscale, ControlNet: dựng workflow trong giao diện ComfyUI, xuất bằng **Save (API Format)**,
thay các giá trị bằng `{{prompt}}`, `{{am}}`, `{{hat_giong}}`, `{{rong}}`, `{{cao}}`, lưu vào repo rồi khai báo
`anh_ai.workflow: duong/dan/workflow.json`.
