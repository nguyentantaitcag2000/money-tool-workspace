# 0. GLOBAL CONSTANTS
# Ensure all Telegram operations target this ID
TARGET_GROUP_ID = "-866483066"

# 1. VARIABLE DEFINITION
# Triggered after successful execution of download-files.py
NEW_DOWNLOAD_COMPLETED = true 

IF NEW_DOWNLOAD_COMPLETED:
    # Logic: Date count from filenames determines single vs. double day title
    VIDEO_FILES = <files in telegram-skills/videos>
    UNIQUE_DATES = unique(<extract date from VIDEO_FILES>)
    DATE_COUNT = len(UNIQUE_DATES)

    # Logic: YouTube determines the starting number sequence
    LATEST_TITLE = <latest title from Talilow YouTube channel>
    MAX_DAY = max(<integers after "Day" in LATEST_TITLE>)
    
    NEXT_START = MAX_DAY + 1
    IF DATE_COUNT == 1:
        DAY_LABEL = "Day " + NEXT_START
    ELSE:
        # If multiple dates found in batch, increment for a range title
        DAY_LABEL = "Day " + NEXT_START + ", " + (NEXT_START + 1)

    SUFFIX = substring of LATEST_TITLE after "-"
    TITLE_VIDEO = DAY_LABEL + " - " + SUFFIX

# 2. PUBLISH RULE
LATEST_YT = <latest video from Talilow>
BASE_DATE = LATEST_YT.publishAt OR LATEST_YT.publishedAt
NEXT_PUB_UTC = (BASE_DATE + 1 day) at 09:00 (Asia/Ho_Chi_Minh) -> UTC ISO format

# 3. EXECUTION STEPS
1. **Cleanup**: Clear `telegram-skills/videos/*` and `edit-video/final-gym.mp4`.
2. **Download**: In `telegram-skills`, run:
   `python download-files.py --group-id={TARGET_GROUP_ID}`
3. **Sync**: Clear `edit-video/config-edit-video-with-scene/folder_videos/*`. 
   Link `telegram-skills/videos` files to this folder.
4. **Process**: In `edit-video`, run:
   `caffeinate python edit-video-gym.py config-edit-video-with-scene/folder_videos config-edit-video-with-scene/folder_audios --output final-gym.mp4 --skip 8 --texts '[{"text": "{DAY_LABEL}","start":2,"duration":5,"font_size":120,"x":"(w-text_w)/2","y":"(h-text_h)/2"}]'`

5. **Upload**: Post `final-gym.mp4` to YouTube (Talilow).
   - Title: `{TITLE_VIDEO}` | Playlist: `Becoming a Better Me`
   - Schedule: `{NEXT_PUB_UTC}` | Privacy: `private`.

6. **Notify**: Use your Telegram tool to send message to `TARGET_GROUP_ID`:
   "Task Complete. #SUCCESS_MARKER_GYM_V2#"