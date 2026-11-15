# Bộ script làm video hoạt hình 2.5D (Tập 1 + Tập 2)

Nhân vật 2D phẳng trong thế giới 3D dựng hoàn toàn bằng code: Blender + Python, ghép bằng FFmpeg.
Bộ này **chỉ có script**. Không kèm voice, nhân vật đã render hay khung hình, vì các script tự tạo ra chúng.

## Cần cài
- **Blender 5.x** (bản 4.2 trở lên cũng chạy được, có thể phải sửa nhẹ)
- **Python 3.10+** và các gói: `pip install pillow numpy openai-whisper`
- **FFmpeg** (có trong PATH)

## Thứ tự chạy

| Bước | Lệnh | Ra cái gì |
|---|---|---|
| 1. Voice | ElevenLabs v3 (dán `tap2/script_elevenlabs.txt`) hoặc `python tools/fish_tts.py --file <kịch bản> -o vo --join` | file mp3 |
| 2. Mốc thời gian | `whisper voice.mp3 --language vi --model small --word_timestamps True --output_format json` | mốc giây của từng chữ (đọc lại, sửa chữ sai) |
| 3. Shot list | sửa bảng `SHOTS` trong `tap2/timeline.py`, rồi chạy `python tap2/timeline.py` | `timeline.json` |
| 4. Nhân vật + texture | `python blender/make_chars.py` và `python blender/make_textures.py` | PNG nền trong suốt |
| 5. Dựng set 3D | `blender -b --python blender/build_scene.py` (đặt `EP=2` để dựng Tập 2) | `episode.blend` |
| 6. Xem thử | `blender -b episode2.blend --python blender/stills2.py` | ảnh thử của từng shot |
| 7. Render | `blender -b episode2.blend -o //frames2/f_#### -F PNG -s <đầu> -e <cuối> -j 2 -a` | khung hình (on twos) |
| 8. Ghép + phụ đề | `python tap2/compose.py` rồi `python tap2/make_final.py` | MP4 1080×1920 30fps |

## Các file chính
- `blender/build_scene.py`: gác mái, phim trường, phố đêm; nhân vật cắt giấy (Emission + Alpha, bóng tiếp xúc); Freestyle.
- `blender/ep1_anim.py`, `blender/ep2_anim.py`: chuyển động, ánh sáng và camera của từng tập (mỗi shot một camera gắn vào marker).
- `blender/make_chars.py`: vẽ nhân vật bằng PIL (10 biểu cảm, mỗi biểu cảm một PNG).
- `tap2/compose.py`: ghép frame 3D với các bảng hướng dẫn (code, terminal, settings) và thanh tiến độ các bước.
- `tap2/make_final.py`: phụ đề 1–2 chữ (ASS), ghép tiếng, đổi on twos thành 30fps.
- `tools/fish_tts.py`: tạo giọng bằng API Fish Audio. Đặt key của bạn vào file `.env` (`FISH_API_KEY=...`), **đừng chia sẻ key**.

## Lưu ý
- Đường dẫn trong script đang theo máy của mình (`D:\2.5D\...`). Bạn sửa lại cho khớp với máy của mình.
- Phần nhạc nền và mix âm thanh của mình dùng một bộ công cụ riêng, không nằm trong gói này. Bạn có thể ghép voice với nhạc của mình bằng FFmpeg (`-filter_complex amix`).
- Render ở 720p rồi phóng lên 1080p, cùng với render on twos, giúp máy yếu (card onboard) chạy nhanh gấp khoảng 4 lần.
