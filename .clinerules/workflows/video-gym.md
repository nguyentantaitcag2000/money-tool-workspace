# 1. VARIABLE DEFINITION
NEW_DOWNLOAD_COMPLETED = true (Triggered after `python app.py`)

IF NEW_DOWNLOAD_COMPLETED:
    # Logic: Date count determines single vs. double day title
    VIDEO_FILES = <files in telegram-skills/videos>
    UNIQUE_DATES = unique(<extract date from VIDEO_FILES>)
    DATE_COUNT = len(UNIQUE_DATES)

    # Logic: YouTube determines the starting number
    LATEST_TITLE = <latest title from Talilow>
    MAX_DAY = max(<integers after "Day" in LATEST_TITLE>)
    
    NEXT_START = MAX_DAY + 1
    IF DATE_COUNT == 1:
        DAY_LABEL = "Day " + NEXT_START
    ELSE:
        # If multiple dates found, increment for a range title
        DAY_LABEL = "Day " + NEXT_START + ", " + (NEXT_START + 1)

    SUFFIX = substring of LATEST_TITLE after "-"
    TITLE_VIDEO = DAY_LABEL + " - " + SUFFIX

# 2. PUBLISH RULE
LATEST_YT = <latest video from Talilow>
BASE_DATE = LATEST_YT.publishAt OR LATEST_YT.publishedAt
NEXT_PUB_UTC = (BASE_DATE + 1 day) at 09:00 (Asia/Ho_Chi_Minh) -> UTC ISO format

# 3. EXECUTION STEPS
1. **Cleanup**: Clear `telegram-skills/videos/*` and `edit-video/final-gym.mp4`.
2. **Download**: Run `python download-files.py --group-id=-866483066` in `telegram-skills`.
3. **Sync**: Clear `edit-video/config-edit-video-with-scene/folder_videos/*`. 
   Link `telegram-skills/videos` files to this folder.
4. **Process**: In `edit-video`, run:
   `caffeinate python edit-video-gym.py config-edit-video-with-scene/folder_videos config-edit-video-with-scene/folder_audios --output final-gym.mp4 --skip 8 --texts '[{"text": "{DAY_LABEL}","start":2,"duration":5,"font_size":120,"x":"(w-text_w)/2","y":"(h-text_h)/2"}]'`
5. **Upload**: Post `final-gym.mp4` to YouTube (Talilow).
   - Title: `{TITLE_VIDEO}` | Playlist: `Becoming a Better Me`
   - Schedule: `{NEXT_PUB_UTC}` | Privacy: `private`.
6. **Notify**: Telegram `Lazycodet [ CRON ]`: "Task Complete. #SUCCESS_MARKER_GYM_V2#"