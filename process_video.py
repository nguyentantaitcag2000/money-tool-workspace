#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys
import re
import time
import ssl
import requests
from datetime import datetime, timedelta
import socket

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import googleapiclient.http
from googleapiclient.errors import HttpError
import json
from dotenv import load_dotenv
from video_preview import confirm_video_preview
load_dotenv()

BASE_DIR = "/Users/tainguyen/Programing/Python/Money-Tool"
CONFIG_DIR = os.path.join(BASE_DIR, "config")
EDIT_VIDEO_DIR = os.path.join(BASE_DIR, "edit-video")
sys.path.insert(0, EDIT_VIDEO_DIR)

from filename_markers import has_trim_markers, trim_video_to_file
secret_path = os.getenv("CLIENT_SECRET_PATH", "client_secret.json")
TOKEN_CACHE_PATH = os.path.join(BASE_DIR, "token_cache.json")
CONFIG = {
    "gym": {
        "GROUP_ID": "-866483066",
        "MARKER": "#SUCCESS_MARKER_GYM_V2#",
        "PLAYLIST_ID": "PL6vRTrd-KXO7_kb8LgOyF8zdnzLQ6i60T",
        "PUBLISH_HOUR": 7,
        "OUTPUT": "final-gym.mp4",
        "CUT_START": "8",
        "CUT_END": "1",
    },
    "lazytyping": {
        "GROUP_ID": "-5200249717",
        "MARKER": "#SUCCESS_MARKER_LAZYTYPING_V1#",
        "PLAYLIST_ID": "PL6vRTrd-KXO7K18TJb_sel2-rtJxU_8WJ",
        "PUBLISH_HOUR": 9,
        "OUTPUT": "final-lazy.mp4",
        "CUT_START": "5",
        "CUT_END": "1",
    },
    "guitar": {
        "GROUP_ID": "-5261026148",
        "MARKER": "#SUCCESS_MARKER_GUITAR_V1#",
        "PLAYLIST_ID": "PL6vRTrd-KXO7L6pqBPGA5fDtOQ_MDnOBI",
        "PUBLISH_HOUR": 8,
        "OUTPUT": "final-guitar.mp4",
        "CUT_START": "5",
        "CUT_END": "1",
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

def enable_ipv4_fallback():
    old_getaddrinfo = socket.getaddrinfo

    def force_ipv4(*args, **kwargs):
        return [
            info
            for info in old_getaddrinfo(*args, **kwargs)
            if info[0] == socket.AF_INET
        ]

    socket.getaddrinfo = force_ipv4

    print("⚠️ IPv6 issue detected -> forcing IPv4")

# =========================
# UTIL
# =========================

def run(cmd, cwd=None):
    print(f"\n🚀 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print("❌ ERROR")
        sys.exit(1)


def load_playlist_config(playlist_type):
    playlist_dir = os.path.join(CONFIG_DIR, playlist_type)
    description_path = os.path.join(playlist_dir, "description.txt")

    playlist_config = {
        "description": None,
        "suffix": None,
    }

    title_path = os.path.join(playlist_dir, "title.txt")

    if os.path.exists(description_path):
        with open(description_path, "r", encoding="utf-8") as file_handle:
            description = file_handle.read().strip()
            if description:
                playlist_config["description"] = description

    if os.path.exists(title_path):
        with open(title_path, "r", encoding="utf-8") as file_handle:
            suffix = file_handle.read().strip()
            if suffix:
                playlist_config["suffix"] = suffix

    return playlist_config

# =========================
# YOUTUBE AUTH
# =========================

def get_youtube_service():
    creds = None

    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH, "r") as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_CACHE_PATH, "w") as f:
        f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

# =========================
# YOUTUBE FETCH
# =========================

def get_playlist_videos(youtube, playlist_id):
    items = []
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )

    while request:
        try:
            response = request.execute()
        except HttpError as e:
            if e.resp.status == 404:
                print(f"⚠️ Playlist page not found (stale pageToken), stopping pagination with {len(items)} items.")
                break
            raise
        items.extend(response.get("items", []))
        request = youtube.playlistItems().list_next(request, response)

    return items

def get_latest_video_info(items):
    if not items:
        return None

    items.sort(key=lambda x: x["snippet"]["publishedAt"], reverse=True)

    for item in items:
        title = item["snippet"]["title"]
        if re.search(r'Day\s+(\d+)', title):
            return title

    return None

# =========================
# TITLE
# =========================

def extract_day_and_suffix(title):
    m = re.search(r'Day\s+(\d+)', title)
    if not m:
        raise Exception("Invalid title format")

    max_day = int(m.group(1))
    suffix = title.split(" - ", 1)[1] if " - " in title else ""
    return max_day, suffix

def extract_dates(files):
    dates = set()

    for f in files:
        m1 = re.search(r'(20\d{2}-\d{2}-\d{2})', f)
        m2 = re.search(r'(20\d{2})(\d{2})(\d{2})', f)

        if m1:
            dates.add(m1.group(1))
        elif m2:
            y, m, d = m2.groups()
            dates.add(f"{y}-{m}-{d}")

    return dates

def generate_title(latest_title, files, suffix):
    max_day, _ = extract_day_and_suffix(latest_title) if latest_title else (0, None)
    dates = extract_dates(files)

    next_day = max_day + 1

    if len(dates) == 1:
        day_label = f"Day {next_day}"
    else:
        day_label = f"Day {next_day}, {next_day + 1}"

    return day_label, f"{day_label} - {suffix}"

# =========================
# SCHEDULE
# =========================

def compute_next_publish(items, publish_hour):
    if not items:
        return None

    used_dates = set()

    for item in items:
        title = item["snippet"]["title"]
        if not re.search(r'Day\s+(\d+)', title):
            continue
        dt = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
        used_dates.add(dt.date())

    if not used_dates:
        return None

    latest = max(used_dates)
    current = latest + timedelta(days=1)

    while current in used_dates:
        current += timedelta(days=1)

    now = datetime.now()

    if current == now.date():
        return None

    dt_local = datetime(current.year, current.month, current.day, publish_hour, 0, 0)
    dt_utc = dt_local - timedelta(hours=7)

    return dt_utc.isoformat() + "Z"

# =========================
# UPLOAD
# =========================

TRANSIENT_UPLOAD_ERRORS = (
    ConnectionResetError,
    BrokenPipeError,
    TimeoutError,
    ssl.SSLError,
    socket.timeout,
)

def _build_upload_request(youtube, file_path, title, publish_time_utc, description, media=None):
    status = {}

    if publish_time_utc:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_time_utc
    else:
        status["privacyStatus"] = "public"

    body = {
        "snippet": {
            "title": title,
            "categoryId": "22"
        },
        "status": status
    }

    if description:
        body["snippet"]["description"] = description

    if publish_time_utc:
        body["status"]["publishAt"] = publish_time_utc

    if media is None:
        media = googleapiclient.http.MediaFileUpload(file_path, resumable=True)

    return youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    ), media


def upload_video(youtube, file_path, title, publish_time_utc, description=None, max_retries=5):
    request, media = _build_upload_request(
        youtube, file_path, title, publish_time_utc, description
    )

    print("📤 Uploading...")

    response = None
    retries = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"{int(status.progress() * 100)}%")
            retries = 0
        except TRANSIENT_UPLOAD_ERRORS as exc:
            retries += 1
            if retries > max_retries:
                raise
            wait = min(2 ** retries, 30)
            print(
                f"⚠️ Mất kết nối ({type(exc).__name__}), "
                f"thử lại sau {wait}s ({retries}/{max_retries})..."
            )
            time.sleep(wait)
        except HttpError as exc:
            if exc.resp.status in (401, 403) and retries < max_retries:
                retries += 1
                wait = min(2 ** retries, 30)
                print(
                    f"⚠️ Token hết hạn hoặc không hợp lệ, "
                    f"làm mới và thử lại sau {wait}s ({retries}/{max_retries})..."
                )
                time.sleep(wait)
                youtube = get_youtube_service()
                request, media = _build_upload_request(
                    youtube, file_path, title, publish_time_utc, description, media=media
                )
            elif exc.resp.status >= 500 and retries < max_retries:
                retries += 1
                wait = min(2 ** retries, 30)
                print(
                    f"⚠️ Lỗi server YouTube ({exc.resp.status}), "
                    f"thử lại sau {wait}s ({retries}/{max_retries})..."
                )
                time.sleep(wait)
            else:
                raise
        except OSError as exc:
            if exc.errno not in (54, 32, 104, 110) or retries >= max_retries:
                raise
            retries += 1
            wait = min(2 ** retries, 30)
            print(
                f"⚠️ Lỗi mạng ({exc}), "
                f"thử lại sau {wait}s ({retries}/{max_retries})..."
            )
            time.sleep(wait)

    return response["id"]

def add_to_playlist(youtube, video_id, playlist_id):
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    ).execute()

def check_secret_exists(path):
    if not os.path.exists(path):
        print(f"❌ Health Check Failed: File {path} not found.")
        return False
    if os.path.getsize(path) == 0:
        print("❌ Health Check Failed: Secret file is empty.")
        return False
    return True

def health_check_api(youtube):
    try:
        youtube.channels().list(
            part="id",
            mine=True
        ).execute(num_retries=3)

        print("✅ Health Check: Authentication is valid.")
        return True

    except TimeoutError:
        print("⚠️ Timeout detected during API call")
        raise

    except Exception as e:
        print(f"❌ Health Check Failed: {repr(e)}")
        return False


def telegram_manifest_path(group_id):
    sanitized = re.sub(r"[^\w.-]", "_", group_id.lstrip("-"))
    return os.path.join(BASE_DIR, "telegram-skills", "cache", f"{sanitized}.json")


def load_telegram_batch_files(group_id, video_dir):
    manifest_path = telegram_manifest_path(group_id)
    if not os.path.exists(manifest_path):
        return []

    with open(manifest_path, "r", encoding="utf-8") as file_handle:
        manifest = json.load(file_handle)

    batch_files = []
    for entry in manifest.get("files", {}).values():
        local_path = entry.get("local_path")
        if not local_path:
            continue

        if os.path.isabs(local_path):
            full_path = local_path
        else:
            full_path = os.path.join(video_dir, os.path.basename(local_path))

        if os.path.isfile(full_path):
            batch_files.append(full_path)

    return batch_files

# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["gym", "lazytyping", "guitar"])
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Xem trước video sau khi dựng xong; Next để upload, Cancel để dừng",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Bỏ qua cache Telegram và tải lại toàn bộ batch",
    )
    parser.add_argument(
        "--force-cleanup",
        action="store_true",
        help="Chạy strong_cleanup.sh để xóa cache video (reset hoàn toàn)",
    )
    args = parser.parse_args()

    cfg = CONFIG[args.type]
    playlist_config = load_playlist_config(args.type)

    # 1. Check file secret cục bộ
    if not check_secret_exists(secret_path):
        sys.exit(1)

    # 2. Khởi tạo service
    try:
        youtube = get_youtube_service()

        if not health_check_api(youtube):
            sys.exit(1)

    except TimeoutError:
        print("Retrying with IPv4 fallback...")

        enable_ipv4_fallback()

        youtube = get_youtube_service()

        if not health_check_api(youtube):
            sys.exit(1)

    # 1. CLEANUP
    if args.force_cleanup:
        run(f"bash {BASE_DIR}/strong_cleanup.sh")
    else:
        run(f"bash {BASE_DIR}/light_cleanup.sh")

    # 2. YOUTUBE DATA
    items = get_playlist_videos(youtube, cfg["PLAYLIST_ID"])

    latest_title = get_latest_video_info(items)

    print(f"🎬 Latest: {latest_title}")

    # 3. DOWNLOAD TELEGRAM
    TELEGRAM_PYTHON = sys.executable
    download_cmd = (
        f"{TELEGRAM_PYTHON} download-files.py "
        f"--group-id={cfg['GROUP_ID']} --marker-text={cfg['MARKER']}"
    )
    if args.force_download:
        download_cmd += " --force-download"
    run(download_cmd, cwd=f"{BASE_DIR}/telegram-skills")

    video_dir = f"{BASE_DIR}/telegram-skills/videos"
    edit_dir = EDIT_VIDEO_DIR

    os.makedirs(f"{edit_dir}/config-edit-video-with-scene/folder_videos", exist_ok=True)

    batch_files = load_telegram_batch_files(cfg["GROUP_ID"], video_dir)
    if not batch_files:
        print(
            "❌ Không có video batch từ Telegram (manifest rỗng hoặc thiếu file).\n"
            "   Chạy lại download hoặc dùng --force-download nếu cần."
        )
        sys.exit(1)

    local_video_count = sum(
        1
        for filename in os.listdir(video_dir)
        if os.path.isfile(os.path.join(video_dir, filename))
    )
    if local_video_count > len(batch_files):
        print(
            f"ℹ️  Thư mục local có {local_video_count} file, "
            f"batch Telegram hiện tại {len(batch_files)} — chỉ dùng {len(batch_files)} file trong manifest."
        )

    keep_count = 0
    normal_files = []

    for src in batch_files:
        filename = os.path.basename(src)

        if "keep" in filename:
            keep_dst = f"{edit_dir}/keep.mp4"
            try:
                overrides = trim_video_to_file(
                    src, keep_dst, filename, default_skip=0, default_trim_end=0
                )
            except (subprocess.CalledProcessError, ValueError) as exc:
                print(f"❌ Không thể xử lý keep video {filename}: {exc}")
                sys.exit(1)
            if has_trim_markers(overrides):
                parts = [token for token in (overrides["skip"], overrides["trim_end"]) if token]
                print(f"✂️  keep video: {filename} → đã cắt theo {', '.join(parts)}")
            keep_count += 1
        else:
            run(f"cp '{src}' {edit_dir}/config-edit-video-with-scene/folder_videos/")
            normal_files.append(filename)

    if len(normal_files) == 0:
        print("❌ No videos")
        sys.exit(1)

    if keep_count > 1:
        print("❌ Multiple keep videos")
        sys.exit(1)

    # 4. TITLE
    day_label, title_video = generate_title(latest_title, normal_files, playlist_config["suffix"])

    # 5. SCHEDULE
    next_pub = compute_next_publish(items, cfg["PUBLISH_HOUR"])

    # 6. EDIT VIDEO
    run(
        f"""
python edit-video-gym.py \
config-edit-video-with-scene/folder_videos \
config-edit-video-with-scene/folder_audios \
--output {cfg['OUTPUT']} \
--skip {cfg['CUT_START']} \
--trim-end {cfg['CUT_END']} \
--type {args.type} \
--config-dir {CONFIG_DIR} \
--texts '[{{"text":"{day_label}","start":2,"duration":5,"font_size":120,"x":"(w-text_w)/2","y":"(h-text_h)/2"}}]'
""",
        cwd=edit_dir
    )

    # 7. CONCAT
    final_video = cfg["OUTPUT"]

    if os.path.exists(f"{edit_dir}/keep.mp4"):
        run(f"python3 concat-videos.py {cfg['OUTPUT']} keep.mp4", cwd=edit_dir)
        run("mv output.mp4 final-with-keep.mp4", cwd=edit_dir)
        final_video = "final-with-keep.mp4"

    final_video_path = os.path.join(edit_dir, final_video)

    if args.preview:
        print("\n👀 Mở cửa sổ xem trước video...")
        if not confirm_video_preview(final_video_path, title=title_video):
            print("🛑 Đã huỷ — bỏ qua upload YouTube, Threads và thông báo Telegram.")
            sys.exit(0)
        print("✅ Đã xác nhận — tiếp tục upload.")

    # Làm mới kết nối sau khi preview (máy sleep / idle lâu có thể làm đứt SSL)
    print("🔄 Làm mới kết nối YouTube trước khi upload...")
    youtube = get_youtube_service()
    if not health_check_api(youtube):
        sys.exit(1)

    # 8. UPLOAD
    video_id = upload_video(
        youtube,
        final_video_path,
        title_video,
        next_pub,
        description=playlist_config["description"]
    )

    add_to_playlist(youtube, video_id, cfg["PLAYLIST_ID"])

    # 9. UPLOAD TO THREADS
    playwright_dir = f"{BASE_DIR}/playwright"
    threads_video = final_video_path
    run(
        f'npx ts-node src/scenarios/threads-upload.ts --video "{threads_video}" --caption "{title_video}"',
        cwd=playwright_dir
    )

    # 10. NOTIFY
    run(
        f'{TELEGRAM_PYTHON} send-message.py --group-id={cfg["GROUP_ID"]} --message="Task Complete. {cfg["MARKER"]}"',
        cwd=f"{BASE_DIR}/telegram-skills"
    )

    print("✅ DONE")


if __name__ == "__main__":
    main()
