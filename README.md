# Hoạt hình lịch sử Việt Nam bằng code

Làm phim hoạt hình hoàn toàn bằng công cụ miễn phí, chạy trên máy, không tốn API:
**Blender + Python + FFmpeg**. Máy mục tiêu: GTX 1660 Super (6GB VRAM).

## Pipeline

```
Kịch bản ──► Chia shot ──► Giọng + mốc thời gian ──► Render từng clip (Blender) ──► Ghép phim (FFmpeg)
```

| Bước | Công cụ | Ra cái gì |
|---|---|---|
| 1. Kịch bản | Viết theo mẫu có cấu trúc (`kich-ban/`) | Cảnh, nhân vật, lời thoại, cảm xúc, hành động |
| 2. Chia shot | Script Python (`pipeline/`) | `shots.json` |
| 3. Giọng đọc | Tự thu âm, hoặc Piper TTS (offline, có tiếng Việt) | Âm thanh từng câu |
| 4. Mốc thời gian + nhép miệng | Whisper, Rhubarb Lip Sync | Thời lượng shot, khẩu hình |
| 5. Render | Blender Eevee, shader toon, Freestyle | Mỗi shot một clip |
| 6. Ghép phim | FFmpeg (NVENC) | MP4 hoàn chỉnh, phụ đề, nhạc |

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `kich-ban/` | Kịch bản theo mẫu có cấu trúc |
| `pipeline/` | Script chia shot, render tự động, ghép phim |
| `assets/` | Nhân vật, mô hình, texture, hoa văn (chỉ để tài nguyên có giấy phép rõ ràng) |
| `docs/` | Ghi chú công cụ, nguồn tài nguyên, tối ưu, từ khóa tìm hiểu |
| `tham-khao/2.5D_scripts/` | Bộ script 2.5D gốc (người khác chia sẻ), giữ nguyên để tham khảo |

Xem [`docs/ghi-chu.md`](docs/ghi-chu.md) để biết chi tiết về hướng làm, nguồn tài nguyên và cách tối ưu.

## Chia việc

- **Trên cloud (Claude)**: viết code dựng mô hình khó, shader, hoa văn; render ảnh xem trước độ phân giải thấp; đẩy lên repo.
- **Trên máy bạn**: `git pull`, render bản chính thức bằng GPU, ghép phim.

## Lưu ý

- Không commit file `.env` hay khóa API. `.gitignore` đã chặn sẵn.
- `tham-khao/2.5D_scripts` là code của người khác, chưa rõ giấy phép. Repo nên để private.
