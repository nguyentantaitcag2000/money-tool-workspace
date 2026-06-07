# Money-Tool

## Loại trừ bài hát khỏi random audio

Khi dựng video, script `edit-video/edit-video-gym.py` chọn ngẫu nhiên một bài từ `edit-video/config-edit-video-with-scene/folder_audios/`. Nếu có bài không muốn dùng nữa, thêm tên vào file config bên dưới — không cần xóa file `.webm` / `.wav` hay file cut-points `.txt` khỏi thư mục nhạc.

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

Các loại khác: `--type guitar`, `--type lazytyping`.

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

Khi có bài bị loại, log sẽ hiện dòng `🚫 Loại trừ N bài hát: ...`.
