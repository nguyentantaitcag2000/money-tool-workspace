# 0. GLOBAL CONSTANTS & PREPARATION

TARGET_GROUP_ID="-5200249717"
MARKER_TEXT="#SUCCESS_MARKER_LAZYTYPING_V1#"

# 1. PRE-PROCESSING (REQUISITES)

# Critical: Must be completed BEFORE any script execution.

1. **Fetch YouTube Data**: Get the latest/most recent video from a YouTube playlist **"My Journey to Master 10-Finger Typing - LazyTyping"** on the "Talilow" channel.
2. **Extract Info**:
* `LATEST_TITLE` = Full title of the latest video.
* `MAX_DAY` = The highest number after the word "Day" in `LATEST_TITLE`.
* `SUFFIX` = Everything in `LATEST_TITLE` after the first " - " (dash).


3. **Calculate Schedule**:
* `BASE_DATE` = `publishAt` date of the latest video.
* ✅ **UPDATED Logic (No Time Constraints)**:
  * Start checking from `BASE_DATE + 1 day` (ignore time of day, only check date)
  * If there is **NO VIDEO** (neither published nor scheduled) for this date in the playlist → **PUBLISH IMMEDIATELY NOW** (do not schedule)
  * If there **IS ALREADY** a video (published or scheduled) for this date → increment +1 day and check again
  * Keep incrementing +1 day until find first **EMPTY DATE** with no video in the playlist
  * If empty date is **TODAY** → publish immediately now
  * If empty date is **FUTURE DATE** → schedule for that date at 09:00 (Asia/Ho_Chi_Minh)
* Convert final publish time to `NEXT_PUB_UTC` (ISO UTC format)

# =========================================
# 2. DOWNLOAD
# =========================================

cd telegram-skills
python download-files.py --group-id=${TARGET_GROUP_ID} --marker-text=${MARKER_TEXT}
cd ..


# =========================================
# 3. SPLIT VIDEO
# =========================================

rm -rf edit-video/config-edit-video-with-scene/folder_videos
mkdir -p edit-video/config-edit-video-with-scene/folder_videos

SOURCE_COUNT=0

for file in telegram-skills/videos/*; do
    filename=$(basename "$file")

    if [[ "$filename" == *lazytyping* ]]; then
        echo "👉 Found lazytyping video: $filename"
        cp "$file" edit-video/lazytyping.mp4
    else
        cp "$file" edit-video/config-edit-video-with-scene/folder_videos/
        ((SOURCE_COUNT++))
    fi
done

DEST_COUNT=$(ls edit-video/config-edit-video-with-scene/folder_videos | wc -l)

if [[ $SOURCE_COUNT -ne $DEST_COUNT || $SOURCE_COUNT -eq 0 ]]; then
    echo "❌ ERROR: Video count mismatch or no valid videos"
    exit 1
fi


### Step 4: Dynamic Labeling
# Require READ skill **file_date_recognition_and_comparison**
# Treat different filename styles as the same date if they point to the same calendar day.
# Example:
# - dji_mimo_20260409_064650_0_1775692789643_timelapse.mp4
# - 2026-04-09 06-37-25-lazytyping.mp4
# => both are 2026-04-09
#
# Robust extraction:
# - Supports YYYY-MM-DD (e.g. 2026-04-09)
# - Supports YYYYMMDD   (e.g. 20260409)
# - Normalizes everything to YYYY-MM-DD before counting unique days
UNIQUE_DATES="$(# AI will extract unique dates from filenames here)"
DATE_COUNT=$(echo "$UNIQUE_DATES" | wc -l)

NEXT_START=$((MAX_DAY + 1))

if [[ $DATE_COUNT -eq 1 ]]; then
    DAY_LABEL="Day ${NEXT_START}"
else
    DAY_LABEL="Day ${NEXT_START}, $((NEXT_START + 1))"
fi

TITLE_VIDEO="${DAY_LABEL} - ${SUFFIX}"


# =========================================
# 5. EDIT VIDEO (MAIN)
# =========================================

cd edit-video

python edit-video-gym.py \
config-edit-video-with-scene/folder_videos \
config-edit-video-with-scene/folder_audios \
--output final-lazy.mp4 \
--skip 5 \
--trim-end 1 \
--texts "[{\"text\": \"${DAY_LABEL}\",\"start\":2,\"duration\":5,\"font_size\":120,\"x\":\"(w-text_w)/2\",\"y\":\"(h-text_h)/2\"}]"


# =========================================
# 6. CONCAT
# =========================================

if [[ -f "lazytyping.mp4" ]]; then
    echo "🎬 Concatenating lazytyping..."

    python3 concat-videos.py final-lazy.mp4 lazytyping.mp4

    mv output.mp4 final-with-lazy.mp4
    FINAL_VIDEO="final-with-lazy.mp4"
else
    FINAL_VIDEO="final-lazy.mp4"
fi

cd ..


# =========================================
# 7. UPLOAD YOUTUBE
# =========================================

# Upload $FINAL_VIDEO
# Title: $TITLE_VIDEO
# Schedule: $NEXT_PUB_UTC

### Step 8: Add to Playlist

# Add VIDEO_ID to playlist: My Journey to Master 10-Finger Typing - LazyTyping


# =========================================
# 8. NOTIFY
# =========================================

cd telegram-skills
python send-message.py --group-id=${TARGET_GROUP_ID} --message="Task Complete. ${MARKER_TEXT}"
cd ..