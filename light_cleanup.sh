#!/bin/bash
# Light cleanup for Money-Tool video workflow
# Clears edit-video artifacts only; keeps telegram-skills/videos cache.

set -e

FOLDER_VIDEOS="edit-video/config-edit-video-with-scene/folder_videos"
EDIT_VIDEO_DIR="edit-video"

if [ -d "$FOLDER_VIDEOS" ]; then
    rm -rf "$FOLDER_VIDEOS"/*
    echo "Emptied $FOLDER_VIDEOS"
else
    echo "$FOLDER_VIDEOS does not exist, creating..."
    mkdir -p "$FOLDER_VIDEOS"
fi

find "$EDIT_VIDEO_DIR" -maxdepth 1 -type f -name 'final*.mp4' -exec rm -f {} +
find "$EDIT_VIDEO_DIR" -maxdepth 1 -type f -name 'keep.mp4' -exec rm -f {} +
find "$EDIT_VIDEO_DIR" -maxdepth 1 -type f -name 'output.mp4' -exec rm -f {} +

echo "Removed edit-video output artifacts in $EDIT_VIDEO_DIR"
echo "✅ Light cleanup complete."
