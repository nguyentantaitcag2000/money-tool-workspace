# 0. GLOBAL CONSTANTS

TARGET_GROUP_ID = "-866483066"
MARKER_TEXT = "#SUCCESS_MARKER_GYM_V2#"

# 1. PRE-PROCESSING (REQUISITES)

# Critical: Must be completed BEFORE any script execution.

1. **Fetch YouTube Data**: Get the latest video from "Talilow" channel.
2. **Extract Info**:
* `LATEST_TITLE` = Full title of the latest video.
* `MAX_DAY` = The highest number after the word "Day" in `LATEST_TITLE`.
* `SUFFIX` = Everything in `LATEST_TITLE` after the first " - " (dash).


3. **Calculate Schedule**:
* `BASE_DATE` = `publishAt` date of the latest video.
* `NEXT_PUB_UTC` = (`BASE_DATE` + 1 day) at 09:00 (Asia/Ho_Chi_Minh) -> Convert to ISO UTC.



# 2. EXECUTION STEPS

### Step 1: Cleanup & Prep

* `rm -rf telegram-skills/videos && mkdir -p telegram-skills/videos`
* `rm -f edit-video/final-gym.mp4`

### Step 2: Download

* In `telegram-skills`, run: `python download-files.py --group-id={TARGET_GROUP_ID} --marker-text={MARKER_TEXT}`

### Step 3: Sync & Strict Validation

* `rm -rf edit-video/config-edit-video-with-scene/folder_videos && mkdir -p edit-video/config-edit-video-with-scene/folder_videos`
* Link/Copy all files from `telegram-skills/videos` to `edit-video/config-edit-video-with-scene/folder_videos`.
* **CHECK**: Count files in both folders.
**IF Count_Source != Count_Destination OR Count_Source == 0**: STOP and report error.

### Step 4: Dynamic Labeling

* `UNIQUE_DATES` = unique dates extracted from filenames in `telegram-skills/videos`.
* `NEXT_START` = `MAX_DAY` + 1.
* **IF** `len(UNIQUE_DATES)` == 1: `{DAY_LABEL}` = "Day " + `NEXT_START`.
* **ELSE**: `{DAY_LABEL}` = "Day " + `NEXT_START` + ", " + (`NEXT_START` + 1).
* `{TITLE_VIDEO}` = `{DAY_LABEL}` + " - " + `{SUFFIX}`.

### Step 5: Process Video

* In `edit-video`, run:
`caffeinate python edit-video-gym.py config-edit-video-with-scene/folder_videos config-edit-video-with-scene/folder_audios --output final-gym.mp4 --skip 8 --texts '[{"text": "{DAY_LABEL}","start":2,"duration":5,"font_size":120,"x":"(w-text_w)/2","y":"(h-text_h)/2"}]'`

### Step 6: Upload to YouTube

* Upload `final-gym.mp4` to "Talilow" channel.
* **Settings**: Title: `{TITLE_VIDEO}` | Schedule: `{NEXT_PUB_UTC}` | Privacy: `private`.
* **Important**: Capture the `VIDEO_ID` of this new upload.

### Step 7: Add to Playlist (Post-Upload)

* Add the video (`VIDEO_ID` from Step 6) to playlist: `Becoming a Better Me`.

### Step 8: Notify

* Send Telegram message to `TARGET_GROUP_ID`: "Task Complete. {MARKER_TEXT}"