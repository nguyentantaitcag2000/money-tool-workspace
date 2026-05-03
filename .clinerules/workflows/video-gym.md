# 0. GLOBAL CONSTANTS & PREPARATION

TARGET_GROUP_ID="-866483066"
MARKER_TEXT="#SUCCESS_MARKER_GYM_V2#"


# 1. PRE-PROCESSING (REQUISITES)

# Critical: Must be completed BEFORE any script execution.

1. **Fetch YouTube Data**: Get the latest uploaded video from the playlist **"Becoming a Better Me"** on the "Talilow" channel.
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
  * If empty date is **FUTURE DATE** → schedule for that date at 07:00 (Asia/Ho_Chi_Minh)
* Convert final publish time to `NEXT_PUB_UTC` (ISO UTC format)



# 2. EXECUTION STEPS

### Step 1: Download

cd telegram-skills
python download-files.py --group-id=${TARGET_GROUP_ID} --marker-text=${MARKER_TEXT}
cd ..


### Step 2: Split lazytyping & normal videos

Goal:
- Separate "lazytyping" video from normal videos

Strict Rules:
- A file is considered "lazytyping" ONLY IF its filename contains the exact keyword: "lazytyping"
- DO NOT detect lazytyping based on timestamp, pattern, or any other assumption
- DO NOT modify the matching rule

Constraints:
- If NO file contains "lazytyping" → this is valid (no lazytyping today)
- If MORE THAN ONE file contains "lazytyping" → STOP with error
- All other files are considered normal videos

Actions:
1. Create folder: edit-video/config-edit-video-with-scene/folder_videos
2. Loop through all files in telegram-skills/videos:
   - If filename contains "lazytyping":
       → copy to: edit-video/lazytyping.mp4
   - Else:
       → copy to: folder_videos
3. Count:
   - SOURCE_COUNT = number of normal videos
   - DEST_COUNT = number of files in folder_videos
   - LAZY_COUNT = number of lazytyping files

Validation:
- If SOURCE_COUNT != DEST_COUNT OR SOURCE_COUNT == 0 → ERROR
- If LAZY_COUNT > 1 → ERROR
- If LAZY_COUNT == 0 → continue normally (no lazytyping)

Output:
- Normal videos → folder_videos
- Lazytyping (if exists) → edit-video/lazytyping.mp4


### Step 3: Dynamic Labeling
# Require READ skill **file_date_recognition_and_comparison**
UNIQUE_DATES=$(ls telegram-skills/videos | grep -v lazytyping | sed -E 's/.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/' | sort | uniq)
DATE_COUNT=$(echo "$UNIQUE_DATES" | wc -l)

NEXT_START=$((MAX_DAY + 1))

if [[ $DATE_COUNT -eq 1 ]]; then
    DAY_LABEL="Day ${NEXT_START}"
else
    DAY_LABEL="Day ${NEXT_START}, $((NEXT_START + 1))"
fi

TITLE_VIDEO="${DAY_LABEL} - ${SUFFIX}"


### Step 4: Process Video (MAIN VIDEO)

cd edit-video

python edit-video-gym.py \
config-edit-video-with-scene/folder_videos \
config-edit-video-with-scene/folder_audios \
--output final-gym.mp4 \
--skip 8 \
--trim-end 1 \
--texts "[{\"text\": \"${DAY_LABEL}\",\"start\":2,\"duration\":5,\"font_size\":120,\"x\":\"(w-text_w)/2\",\"y\":\"(h-text_h)/2\"}]"


### Step 5: Concat lazytyping (if exists)

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


### Step 6: Upload to YouTube

# Upload $FINAL_VIDEO
# Title: $TITLE_VIDEO
# Schedule: $NEXT_PUB_UTC
# Privacy: private

# Capture VIDEO_ID


### Step 7: Add to Playlist

# Add VIDEO_ID to playlist: Becoming a Better Me


### Step 8: Notify & Cleanup

cd telegram-skills
python send-message.py --group-id=${TARGET_GROUP_ID} --message="Task Complete. ${MARKER_TEXT}"
cd ..

