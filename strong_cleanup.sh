#!/bin/bash
# Strong cleanup script for Money-Tool video workflow
# Removes all files in the specified folders and all .mp4 files in edit-video

set -e

# Absolute paths (relative to repo root)
FOLDER1="edit-video/config-edit-video-with-scene/folder_videos"
FOLDER2="telegram-skills/videos"
EDIT_VIDEO_DIR="edit-video"

# Remove all files/folders in FOLDER1
if [ -d "$FOLDER1" ]; then
    rm -rf "$FOLDER1"/*
    echo "Emptied $FOLDER1"
else
    echo "$FOLDER1 does not exist, creating..."
    mkdir -p "$FOLDER1"
fi

# Remove all files/folders in FOLDER2
if [ -d "$FOLDER2" ]; then
    rm -rf "$FOLDER2"/*
    echo "Emptied $FOLDER2"
else
    echo "$FOLDER2 does not exist, creating..."
    mkdir -p "$FOLDER2"
fi

# Remove all .mp4 files in edit-video
find "$EDIT_VIDEO_DIR" -maxdepth 1 -type f -name '*.mp4' -exec rm -f {} +
echo "Removed all .mp4 files in $EDIT_VIDEO_DIR"

echo "✅ Strong cleanup complete."
