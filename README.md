# Money-Tool

## Cài đặt

### Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

| Nhóm | Dùng cho |
|------|----------|
| `google-*`, `requests`, `python-dotenv` | `process_video.py`, upload YouTube |
| `Telethon`, `rich` | `telegram-skills/` (tải video, gửi tin) |
| `opencv-python`, `Pillow` | `--preview` (xem trước video) |
| `numpy`, `pydub`, `tqdm`, `pytest` | Script phụ trong `edit-video/` |

### Công cụ hệ thống (không cài qua pip)

- **ffmpeg** / **ffplay** — dựng video (`edit-video-gym.py`) và phát audio preview  
  `brew install ffmpeg`
- **Node.js** + **npm** — upload Threads (`playwright/`)

## Chọn audio và đồng bộ video

Khi dựng video, script `edit-video/edit-video-gym.py` **phân tích thời lượng video** (sau skip/trim), so sánh với cut-points của từng bài trong `edit-video/config-edit-video-with-scene/folder_audios/`, rồi chọn bài **khớp nhất** (mặc định `--smart-audio`). Dùng `--no-smart-audio` nếu muốn chọn ngẫu nhiên như trước.

Khi video hơi ngắn so với scene (ví dụ 9s cần 10s), script sẽ **kéo dài nhẹ** thay vì ghép clip 1 giây bị tua nhanh. Ngưỡng mặc định: tối đa **2 giây** và **15%** thời lượng video (`--max-stretch-sec`, `--max-stretch-ratio`). Nếu thiếu quá nhiều (ví dụ 9s cần 14s), ghép video tiếp theo bình thường và **tái sử dụng** phần còn dư qua nhiều scene.

## Loại trừ bài hát khỏi danh sách audio

### File config

| File | Phạm vi |
|------|---------|
| `config/excluded_audios.txt` | Loại trừ cho **mọi** loại video |
| `config/gym/excluded_audios.txt` | Chỉ khi chạy `--type gym` |
| `config/guitar/excluded_audios.txt` | Chỉ khi chạy `--type guitar` |
| `config/lazytyping/excluded_audios.txt` | Chỉ khi chạy `--type lazytyping` |

Danh sách loại trừ theo loại video được **cộng thêm** với danh sách global.

### Format

- Một dòng = một bài hát
- Dòng trống hoặc dòng bắt đầu `#` sẽ bị bỏ qua
- Có thể ghi tên file đầy đủ hoặc không có đuôi
- So khớp không phân biệt hoa thường

Ví dụ nội dung `config/excluded_audios.txt`:

```txt
# Bài hát không dùng nữa
thay-doi.webm
# hoặc chỉ tên không đuôi:
# thay-doi
```

### Ví dụ

**Loại một bài cho tất cả video** — thêm vào `config/excluded_audios.txt`:

```txt
thay-doi.webm
```

**Chỉ loại khi chạy gym** — thêm vào `config/gym/excluded_audios.txt` thay vì file global.

### Chạy pipeline

Pipeline tự đọc config qua `--type` và `--config-dir`:

```bash
caffeinate python process_video.py --type gym
```

Thêm `--preview` để xem video sau khi dựng xong; cửa sổ có nút **Next** (tiếp tục upload) và **Cancel** (dừng, không upload):

```bash
caffeinate python process_video.py --type gym --preview
```

Các loại khác: `--type guitar`, `--type lazytyping`.

### Cache download Telegram

Mặc định pipeline **không** xóa video đã tải trong `telegram-skills/videos/`. Trước khi tải, script so khớp batch video trên Telegram với manifest local (khóa file Telegram + SHA256); file đã có và còn nguyên vẹn sẽ được bỏ qua. Chỉ dọn artifact tạm trong `edit-video/` (không đụng cache video).

| Flag | Tác dụng |
|------|----------|
| `--force-download` | Bỏ qua cache, tải lại toàn bộ batch video từ Telegram (dùng khi test hoặc nghi cache lỗi) |
| `--force-cleanup` | Chạy `strong_cleanup.sh` — xóa cache video Telegram và artifact edit-video trước khi chạy (reset hoàn toàn như hành vi cũ) |

Ví dụ:

```bash
# Tải lại dù file local đã có
caffeinate python process_video.py --type gym --force-download

# Reset hoàn toàn cache video + edit artifacts
caffeinate python process_video.py --type gym --force-cleanup
```

Reset thủ công cache (không chạy pipeline): `bash strong_cleanup.sh`

### Kiểm tra nhanh (không render video)

```bash
cd edit-video
python3 edit-video-gym.py \
  config-edit-video-with-scene/folder_videos \
  config-edit-video-with-scene/folder_audios \
  --type gym \
  --config-dir ../config \
  --dry-run
```

Khi có bài bị loại, log sẽ hiện dòng `🚫 Loại trừ N bài hát: ...`. Khi smart audio bật, log còn hiện bài được chọn và top 3 điểm khớp.
