# Giọng đọc bằng VietTTS

[VietTTS](https://github.com/dangvansam/viet-tts) cho giọng tiếng Việt tự nhiên hơn Piper, mỗi nhân vật dùng được
một giọng riêng, và nhân bản được giọng từ một file thu âm mẫu.

## ⚠ Đọc trước khi dùng

- **Không dùng thương mại.** Code VietTTS là Apache 2.0, nhưng **model và giọng mẫu là CC BY-NC**.
  Kênh bật kiếm tiền (YouTube, TikTok...) là dùng thương mại → dùng Piper, hoặc tự thu giọng.
- **Không dùng giọng người nổi tiếng.** Danh sách giọng có sẵn có `son-tung-mtp`, `nsnd-le-chuc`,
  `nguyen-ngoc-ngan`, `jack-sparrow`, `doremon`... Dùng giọng người thật khi chưa được phép là vi phạm quyền
  của họ. Dùng các giọng `speechify_*`, hoặc nhân bản **giọng của chính bạn**.
- Chỉ nhân bản giọng của người đã đồng ý.

## Cài trên Windows (qua Docker)

VietTTS chưa chạy trực tiếp trên Windows, nên dùng Docker Desktop.

1. Cài **Docker Desktop** (bật WSL 2). Driver NVIDIA bạn đã cập nhật nên Docker dùng được GPU.
2. Tải VietTTS về một thư mục **ngoài** repo này, ví dụ `C:\Users\<bạn>\viet-tts`:

```powershell
cd ~
```

```powershell
git clone https://github.com/dangvansam/viet-tts.git
```

```powershell
cd viet-tts
```

3. Build và bật server (lần đầu mất khá lâu vì phải tải model):

```powershell
docker compose build
```

```powershell
docker compose up -d
```

4. Kiểm tra server đã chạy, nếu ra danh sách giọng là được:

```powershell
Invoke-RestMethod http://localhost:8298/v1/voices
```

Tắt server khi không dùng: `docker compose down` (trong thư mục `viet-tts`).

⚠ Mình chưa chạy thử VietTTS trên Windows với GTX 1660 Super. Nếu Docker báo lỗi GPU, gửi ảnh màn hình để mình xử lý.

## Dùng trong kịch bản

```yaml
giong:
  cach: viettts
  may_chu: http://localhost:8298     # mặc định
  giong_mac_dinh: speechify_10       # cho nhân vật không khai báo giọng
  toc_do: 1.0                        # > 1 là đọc chậm hơn

nhan_vat:
  nguoi_ke:
    an_hinh: true
    giong: giong/mau/nguoi_ke.wav    # nhân bản từ file mẫu (giọng của bạn, 5–15 giây, rõ, không nhạc nền)
  nguyen_anh:
    giong: speechify_3               # giọng có sẵn
```

- `giong` là **đường dẫn tới file có thật** thì pipeline nhân bản giọng từ file đó.
- Còn lại thì coi là **tên giọng có sẵn**. Xem danh sách bằng `Invoke-RestMethod http://localhost:8298/v1/voices`.

Rồi chạy như bình thường:

```powershell
python pipeline/chay.py kich-ban/gia_dinh_1788.yaml
```
