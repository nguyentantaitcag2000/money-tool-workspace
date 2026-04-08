# 0. GLOBAL CONSTANTS & PREPARATION

TARGET_GROUP_ID="-5200249717"
MARKER_TEXT="#SUCCESS_MARKER_LAZYTYPING_V1#"

# 1. PRE-PROCESSING (REQUISITES)

# Critical: Must be completed BEFORE any script execution.

1. **Fetch YouTube Data**: Get the latest uploaded video from the playlist **"My Journey to Master 10-Finger Typing - LazyTyping"** on the "Talilow" channel.
2. **Extract Info**:
* `LATEST_TITLE` = Full title of the latest video.
* `MAX_DAY` = The highest number after the word "Day" in `LATEST_TITLE`.
* `SUFFIX` = Everything in `LATEST_TITLE` after the first " - " (dash).


3. **Calculate Schedule**:
* `BASE_DATE` = `publishAt` date of the latest video.
* `NEXT_PUB_UTC` = (`BASE_DATE` + 1 day) at 09:00 (Asia/Ho_Chi_Minh) -> Convert to ISO UTC.



# =========================================
# 2. CLEANUP
# =========================================

rm -rf telegram-skills/videos && mkdir -p telegram-skills/videos
rm -f edit-video/final-lazy.mp4
rm -f edit-video/final-with-lazy.mp4
rm -f edit-video/lazytyping.mp4


# =========================================
# 3. DOWNLOAD
# =========================================

cd telegram-skills
python download-files.py --group-id=${TARGET_GROUP_ID} --marker-text=${MARKER_TEXT}
cd ..


# =========================================
# 4. SPLIT VIDEO
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


### Step 5: Dynamic Labeling

UNIQUE_DATES=$(ls telegram-skills/videos | grep -v lazytyping | sed -E 's/.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/' | sort | uniq)
DATE_COUNT=$(echo "$UNIQUE_DATES" | wc -l)

NEXT_START=$((MAX_DAY + 1))

if [[ $DATE_COUNT -eq 1 ]]; then
    DAY_LABEL="Day ${NEXT_START}"
else
    DAY_LABEL="Day ${NEXT_START}, $((NEXT_START + 1))"
fi

TITLE_VIDEO="${DAY_LABEL} - ${SUFFIX}"


# =========================================
# 6. EDIT VIDEO (MAIN)
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
# 7. CONCAT
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
# 8. UPLOAD YOUTUBE
# =========================================

# Upload $FINAL_VIDEO
# Title: $TITLE_VIDEO
# Schedule: $NEXT_PUB_UTC
# Playlist: LazyTyping


# =========================================
# 9. NOTIFY
# =========================================

cd telegram-skills
python send-message.py --group-id=${TARGET_GROUP_ID} --message="Task Complete. ${MARKER_TEXT}"
cd ..