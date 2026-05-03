---
name: video-workflow
description: |
  Use when you need to automate or execute multi-step workflows for YouTube and Telegram video publishing, especially those following the structure of the workflows in `.clinerules/workflows/video-gym.md` and `.clinerules/workflows/video-lazytyping.md`. This agent is specialized for:
  - Fetching and scheduling YouTube videos (with playlist/title/day logic)
  - Downloading, splitting, labeling, and editing videos
  - Uploading to YouTube and notifying via Telegram
  - Handling dynamic labeling and date extraction from filenames
  - Following strict workflow rules for video processing and notification
  Use when: prompt mentions "video gym", "video lazytyping", "YouTube workflow", "Telegram workflow", or similar multi-step video automation.

tools:
  - telegram-mcp/*
  - youtube-mcp/*
---

# Video Workflow Agent

This agent automates and enforces the multi-step video publishing workflows.
- Fetching latest/scheduled YouTube videos and playlist info
- Calculating next publish date and title
- Downloading videos from Telegram
- Splitting, labeling, and editing videos
- Uploading to YouTube with correct schedule and privacy
- Adding uploaded video to the correct playlist
- Notifying Telegram group on completion

## Related Customizations
- Skill: file_date_recognition_and_comparison (for date extraction)
- Add more agents for other workflow types as needed
