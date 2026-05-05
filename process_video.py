#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys
import re
import requests
from datetime import datetime, timedelta

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import googleapiclient.http
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = "/Users/tainguyen/Programing/Python/Money-Tool"
secret_path = os.getenv("CLIENT_SECRET_PATH", "client_secret.json")
CONFIG = {
    "gym": {
        "GROUP_ID": "-866483066",
        "MARKER": "#SUCCESS_MARKER_GYM_V2#",
        "PLAYLIST_ID": "PL6vRTrd-KXO7_kb8LgOyF8zdnzLQ6i60T",
        "PUBLISH_HOUR": 7,
        "OUTPUT": "final-gym.mp4",
        "SKIP": "8"
    },
    "lazytyping": {
        "GROUP_ID": "-5200249717",
        "MARKER": "#SUCCESS_MARKER_LAZYTYPING_V1#",
        "PLAYLIST_ID": "PL6vRTrd-KXO7K18TJb_sel2-rtJxU_8WJ",
        "PUBLISH_HOUR": 9,
        "OUTPUT": "final-lazy.mp4",
        "SKIP": "5"
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

# =========================
# UTIL
# =========================

def run(cmd, cwd=None):
    print(f"\n🚀 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print("❌ ERROR")
        sys.exit(1)

# =========================
# YOUTUBE AUTH
# =========================

def get_youtube_service():
    flow = InstalledAppFlow.from_client_secrets_file(
        secret_path, SCOPES
    )
    creds = flow.run_local_server(port=0)
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
        response = request.execute()
        items.extend(response.get("items", []))
        request = youtube.playlistItems().list_next(request, response)

    return items

def get_latest_video_info(items):
    items.sort(key=lambda x: x["snippet"]["publishedAt"], reverse=True)
    latest = items[0]["snippet"]

    return latest["title"]

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

def generate_title(latest_title, files):
    max_day, suffix = extract_day_and_suffix(latest_title)
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
    used_dates = set()

    for item in items:
        dt = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
        used_dates.add(dt.date())

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

def upload_video(youtube, file_path, title, publish_time_utc):
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

    if publish_time_utc:
        body["status"]["publishAt"] = publish_time_utc

    media = googleapiclient.http.MediaFileUpload(file_path, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    print("📤 Uploading...")

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"{int(status.progress() * 100)}%")

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
        # Lệnh này chỉ tốn ~1 đơn vị quota (rất rẻ so với 1600 của upload)
        youtube.channels().list(part="id", mine=True).execute()
        print("✅ Health Check: Authentication is valid.")
        return True
    except Exception as e:
        print(f"❌ Health Check: Authentication expired or invalid. Error: {e}")
        return False
    
# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["gym", "lazytyping"])
    args = parser.parse_args()

    cfg = CONFIG[args.type]

    # 1. Check file secret cục bộ
    if not check_secret_exists(secret_path):
        sys.exit(1)

    # 2. Khởi tạo service
    youtube = get_youtube_service()

    # 3. API Health Check trước khi chạy các tác vụ nặng
    if not health_check_api(youtube):
        print("Vui lòng xóa file token cũ và chạy lại để re-auth.")
        sys.exit(1)

    # 1. CLEANUP
    run(f"bash {BASE_DIR}/strong_cleanup.sh")

    # 2. YOUTUBE DATA
    items = get_playlist_videos(youtube, cfg["PLAYLIST_ID"])

    latest_title = get_latest_video_info(items)

    print(f"🎬 Latest: {latest_title}")

    # 3. DOWNLOAD TELEGRAM
    TELEGRAM_PYTHON = sys.executable
    run(
        f"{TELEGRAM_PYTHON} download-files.py --group-id={cfg['GROUP_ID']} --marker-text={cfg['MARKER']}",
        cwd=f"{BASE_DIR}/telegram-skills"
    )

    video_dir = f"{BASE_DIR}/telegram-skills/videos"
    edit_dir = f"{BASE_DIR}/edit-video"

    os.makedirs(f"{edit_dir}/config-edit-video-with-scene/folder_videos", exist_ok=True)

    lazy_count = 0
    normal_files = []

    for f in os.listdir(video_dir):
        src = os.path.join(video_dir, f)

        if "lazytyping" in f:
            run(f"cp '{src}' {edit_dir}/lazytyping.mp4")
            lazy_count += 1
        else:
            run(f"cp '{src}' {edit_dir}/config-edit-video-with-scene/folder_videos/")
            normal_files.append(f)

    if len(normal_files) == 0:
        print("❌ No videos")
        sys.exit(1)

    if lazy_count > 1:
        print("❌ Multiple lazytyping")
        sys.exit(1)

    # 4. TITLE
    day_label, title_video = generate_title(latest_title, normal_files)

    # 5. SCHEDULE
    next_pub = compute_next_publish(items, cfg["PUBLISH_HOUR"])

    # 6. EDIT VIDEO
    run(
        f"""
python edit-video-gym.py \
config-edit-video-with-scene/folder_videos \
config-edit-video-with-scene/folder_audios \
--output {cfg['OUTPUT']} \
--skip {cfg['SKIP']} \
--trim-end 1 \
--texts '[{{"text":"{day_label}","start":2,"duration":5,"font_size":120,"x":"(w-text_w)/2","y":"(h-text_h)/2"}}]'
""",
        cwd=edit_dir
    )

    # 7. CONCAT
    final_video = cfg["OUTPUT"]

    if os.path.exists(f"{edit_dir}/lazytyping.mp4"):
        run(f"python3 concat-videos.py {cfg['OUTPUT']} lazytyping.mp4", cwd=edit_dir)
        run("mv output.mp4 final-with-lazy.mp4", cwd=edit_dir)
        final_video = "final-with-lazy.mp4"

    # 8. UPLOAD
    video_id = upload_video(
        youtube,
        os.path.join(edit_dir, final_video),
        title_video,
        next_pub
    )

    add_to_playlist(youtube, video_id, cfg["PLAYLIST_ID"])

    # 9. NOTIFY
    run(
        f'{TELEGRAM_PYTHON} send-message.py --group-id={cfg["GROUP_ID"]} --message="Task Complete. {cfg["MARKER"]}"',
        cwd=f"{BASE_DIR}/telegram-skills"
    )

    print("✅ DONE")


if __name__ == "__main__":
    main()
