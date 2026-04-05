# 0. GLOBAL CONSTANTS & PREPARATION

TARGET_GROUP_ID="-866483066"
MARKER_TEXT="#SUCCESS_MARKER_GYM_V2#"

# Keep Mac awake
caffeinate -u -t 3600 &


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

rm -rf telegram-skills/videos && mkdir -p telegram-skills/videos
rm -f edit-video/final-gym.mp4
rm -f edit-video/final-with-lazy.mp4
rm -f edit-video/lazytyping.mp4


### Step 2: Download

cd telegram-skills
python download-files.py --group-id=${TARGET_GROUP_ID} --marker-text=${MARKER_TEXT}
cd ..


### Step 3: Split lazytyping & normal videos

LAZY_VIDEO=$(ls telegram-skills/videos | grep -i "lazytyping" | head -n 1)

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

# STRICT CHECK
if [[ $SOURCE_COUNT -ne $DEST_COUNT || $SOURCE_COUNT -eq 0 ]]; then
    echo "❌ ERROR: Video count mismatch or no valid videos"
    exit 1
fi


### Step 4: Dynamic Labeling

UNIQUE_DATES=$(ls telegram-skills/videos | grep -v lazytyping | sed -E 's/.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/' | sort | uniq)
DATE_COUNT=$(echo "$UNIQUE_DATES" | wc -l)

NEXT_START=$((MAX_DAY + 1))

if [[ $DATE_COUNT -eq 1 ]]; then
    DAY_LABEL="Day ${NEXT_START}"
else
    DAY_LABEL="Day ${NEXT_START}, $((NEXT_START + 1))"
fi

TITLE_VIDEO="${DAY_LABEL} - ${SUFFIX}"


### Step 5: Process Video (MAIN VIDEO)

cd edit-video

python edit-video-gym.py \
config-edit-video-with-scene/folder_videos \
config-edit-video-with-scene/folder_audios \
--output final-gym.mp4 \
--skip 8 \
--trim-end 1 \
--texts "[{\"text\": \"${DAY_LABEL}\",\"start\":2,\"duration\":5,\"font_size\":120,\"x\":\"(w-text_w)/2\",\"y\":\"(h-text_h)/2\"}]"


### Step 6: Concat lazytyping (if exists)

if [[ -f "lazytyping.mp4" ]]; then
    echo "🎬 Concatenating lazytyping video..."

    python3 concat-videos.py final-gym.mp4 lazytyping.mp4

    # giả sử script output là output.mp4
    mv output.mp4 final-with-lazy.mp4

    FINAL_VIDEO="final-with-lazy.mp4"
else
    echo "⚠️ No lazytyping video found"
    FINAL_VIDEO="final-gym.mp4"
fi

cd ..


### Step 7: Upload to YouTube

# Upload $FINAL_VIDEO
# Title: $TITLE_VIDEO
# Schedule: $NEXT_PUB_UTC
# Privacy: private

# Capture VIDEO_ID


### Step 8: Add to Playlist

# Add VIDEO_ID to playlist: Becoming a Better Me


### Step 9: Notify & Cleanup

cd telegram-skills
python send-message.py --group-id=${TARGET_GROUP_ID} --message="Task Complete. ${MARKER_TEXT}"
cd ..

# Optional
killall caffeinate
