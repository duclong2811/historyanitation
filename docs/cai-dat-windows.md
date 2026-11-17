# Cài đặt từ đầu trên Windows 10

Làm theo thứ tự. Lệnh chạy trong **PowerShell**. Sau mỗi lần cài bằng `winget`, **đóng PowerShell và mở lại**
để Windows nhận đường dẫn mới.

## 0. Driver NVIDIA

Tải **NVIDIA Studio Driver** mới nhất (bản 610 trở lên) ở https://www.nvidia.com/Download/index.aspx
(GeForce 16 Series → GTX 1660 SUPER → Windows 10 64-bit). Cài, chọn **Custom → Perform a clean installation**,
rồi khởi động lại máy.

## 1. Kiểm tra winget

```powershell
winget --version
```

Báo lỗi không nhận ra lệnh thì mở **Microsoft Store**, tìm **App Installer**, bấm Update/Install, rồi thử lại.

## 2. Công cụ cơ bản

| Công cụ | Dùng để | Bắt buộc? |
|---|---|---|
| Git | Tải và cập nhật repo | ✅ |
| Python 3.11 | Chạy pipeline | ✅ |
| FFmpeg | Ghép phim, xử lý âm thanh | ✅ |
| 7-Zip | Giải nén ComfyUI | ✅ (chế độ ảnh AI) |
| Blender | Chế độ dựng 3D | Chỉ khi dùng chế độ Blender |

```powershell
winget install Git.Git
```

```powershell
winget install Python.Python.3.11
```

```powershell
winget install Gyan.FFmpeg
```

```powershell
winget install 7zip.7zip
```

```powershell
winget install BlenderFoundation.Blender
```

Đóng PowerShell, mở lại, kiểm tra:

```powershell
git --version
```

```powershell
python --version
```

```powershell
ffmpeg -version
```

Gõ `python` mà Microsoft Store bật lên: vào **Settings → Apps → App execution aliases**, tắt hai mục
`python.exe` và `python3.exe`, rồi mở lại PowerShell.

## 3. Repo và thư viện Python

```powershell
cd ~
```

```powershell
git clone https://github.com/duclong2811/historyanitation
```

```powershell
cd historyanitation
```

```powershell
pip install -r requirements.txt
```

Parallax 2.5D (chế độ ảnh AI) cần thêm:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

```powershell
pip install transformers
```

## 4. ComfyUI và model (chế độ ảnh AI)

1. Tải ComfyUI: https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z
2. Chuột phải → **7-Zip → Extract files...**, ô **Extract to** gõ `C:\`. Ra thư mục `C:\ComfyUI_windows_portable`.
3. Tải model và đặt vào đúng chỗ:

| File | Link | Đặt vào |
|---|---|---|
| `animagine-xl-4.0-opt.safetensors` (khoảng 7GB) | https://huggingface.co/cagliostrolab/animagine-xl-4.0/resolve/main/animagine-xl-4.0-opt.safetensors | `C:\ComfyUI_windows_portable\ComfyUI\models\checkpoints\` |
| `RealESRGAN_x4plus_anime_6B.pth` (khoảng 18MB) | https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth | `C:\ComfyUI_windows_portable\ComfyUI\models\upscale_models\` |

Lưu model ở ổ khác (ví dụ `D:\`) một bản dự phòng để lần sau cài lại Windows không phải tải lại.

4. Chạy `C:\ComfyUI_windows_portable\run_nvidia_gpu.bat`, chờ dòng `To see the GUI go to: http://127.0.0.1:8188`.
   Báo lỗi `CUDA` hoặc `no kernel image` thì tải bản có đuôi `cu126` ở trang Releases thay thế.

## 5. Chạy thử

ComfyUI đang mở, trong thư mục repo:

```powershell
python pipeline/chay.py kich-ban/gia_dinh_1788_anime.yaml --xem-thu
```

Ra `build\gia_dinh_1788_anime\xem_thu.png` là xong. Chế độ Blender thử bằng:

```powershell
python pipeline/chay.py kich-ban/mau.yaml --xem-thu
```

## 6. Claude Desktop (skill đạo diễn)

Tải ở https://claude.ai/download, đăng nhập, vào phần **Code**, chọn thư mục `historyanitation`.
Skill `dao-dien` trong repo được nạp tự động (xem README).

## Tùy chọn

- **Docker Desktop**: chỉ cần khi dùng giọng VietTTS, xem `docs/giong-viettts.md`.
- **Đặt tên khi commit** (nếu bạn tự sửa và đẩy code):

```powershell
git config --global user.name "Tên của bạn"
```

```powershell
git config --global user.email "email@cua-ban"
```
