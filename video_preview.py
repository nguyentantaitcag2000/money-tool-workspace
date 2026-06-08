import os
import shutil
import subprocess
import sys


def _format_time(ms):
    if ms < 0:
        ms = 0
    seconds = ms // 1000
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def _find_ffplay():
    ffplay = shutil.which("ffplay")
    if ffplay:
        return ffplay
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        sibling = os.path.join(os.path.dirname(ffmpeg), "ffplay")
        if os.path.isfile(sibling) and os.access(sibling, os.X_OK):
            return sibling
    return None


def _confirm_with_external_player(video_path, title=None):
    """Fallback: mở player ngoài khi chưa cài PyQt6."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        print("❌ Thiếu PyQt6 và tkinter — không thể mở preview.")
        return False

    ffplay = _find_ffplay()
    player_proc = None
    backend = None

    if ffplay:
        player_proc = subprocess.Popen(
            [
                ffplay,
                "-window_title",
                "Xem trước video",
                "-loglevel",
                "quiet",
                video_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        backend = "ffplay"
    elif sys.platform == "darwin":
        subprocess.Popen(["open", video_path])
        backend = "quicktime"
    else:
        print(
            "❌ Cài PyQt6 để xem video nhúng trong cửa sổ:\n"
            "   pip install PyQt6"
        )
        return False

    hint = (
        "Video phát trong ffplay — Space: dừng • ←/→: tua • F: phóng to."
        if backend == "ffplay"
        else "Video phát trong QuickTime — dùng điều khiển của app đó."
    )

    result = {"approved": False}
    header = title or os.path.basename(video_path)

    root = tk.Tk()
    root.title("Xem trước video")
    root.attributes("-topmost", True)
    root.configure(bg="#f0f0f0")
    root.geometry("520x300")

    tk.Label(root, text=header, font=("", 14, "bold"), bg="#f0f0f0").pack(pady=(16, 4))
    tk.Label(root, text=os.path.basename(video_path), fg="#666", bg="#f0f0f0").pack()
    tk.Label(root, text=hint, wraplength=460, bg="#f0f0f0", justify="left").pack(pady=12)

    frame = tk.Frame(root, bg="#f0f0f0")
    frame.pack(fill=tk.X, padx=20, pady=8)

    def finish(approved):
        result["approved"] = approved
        if player_proc and player_proc.poll() is None:
            player_proc.kill()
        root.destroy()

    ttk.Button(frame, text="✓  Tiếp tục upload", command=lambda: finish(True)).pack(
        side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6)
    )
    ttk.Button(frame, text="✕  Huỷ", command=lambda: finish(False)).pack(
        side=tk.LEFT, expand=True, fill=tk.X, padx=(6, 0)
    )
    root.protocol("WM_DELETE_WINDOW", lambda: finish(False))
    root.mainloop()
    return result["approved"]


def _confirm_with_pyqt(video_path, title=None):
    from PyQt6.QtCore import Qt, QUrl
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    from PyQt6.QtWidgets import (
        QApplication,
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QSlider,
        QVBoxLayout,
    )

    app = QApplication.instance() or QApplication([])

    dialog = QDialog()
    dialog.setWindowTitle("Xem trước video")
    dialog.setMinimumSize(420, 640)
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

    screen = app.primaryScreen().availableGeometry()
    video_h = int(screen.height() * 0.62)
    video_w = int(video_h * 9 / 16)
    if video_w > screen.width() * 0.45:
        video_w = int(screen.width() * 0.45)
        video_h = int(video_w * 16 / 9)
    dialog.resize(max(420, video_w + 40), video_h + 220)

    header = title or os.path.basename(video_path)

    root_layout = QVBoxLayout(dialog)
    root_layout.setContentsMargins(16, 14, 16, 16)
    root_layout.setSpacing(10)

    title_label = QLabel(header)
    title_label.setWordWrap(True)
    title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #111;")
    root_layout.addWidget(title_label)

    file_label = QLabel(os.path.basename(video_path))
    file_label.setStyleSheet("color: #666; font-size: 11px;")
    root_layout.addWidget(file_label)

    video_widget = QVideoWidget()
    video_widget.setMinimumSize(video_w, video_h)
    video_widget.setStyleSheet("background-color: #000;")
    root_layout.addWidget(video_widget, stretch=1)

    player = QMediaPlayer()
    audio = QAudioOutput()
    player.setAudioOutput(audio)
    player.setVideoOutput(video_widget)
    player.setSource(QUrl.fromLocalFile(os.path.abspath(video_path)))

    time_label = QLabel("00:00 / 00:00")
    time_label.setStyleSheet(
        "color: #222222; font-family: Menlo, monospace; font-size: 11px;"
    )

    timeline = QSlider(Qt.Orientation.Horizontal)
    timeline.setRange(0, 0)
    seeking = {"active": False}

    def update_timeline(position):
        if seeking["active"] or timeline.maximum() <= 0:
            return
        timeline.setValue(position)
        time_label.setText(
            f"{_format_time(position)} / {_format_time(timeline.maximum())}"
        )

    def on_duration_changed(duration):
        timeline.setRange(0, max(duration, 0))
        update_timeline(player.position())

    def on_slider_pressed():
        seeking["active"] = True

    def on_slider_released():
        seeking["active"] = False
        player.setPosition(timeline.value())

    def on_slider_moved(value):
        if seeking["active"]:
            time_label.setText(
                f"{_format_time(value)} / {_format_time(timeline.maximum())}"
            )

    player.positionChanged.connect(update_timeline)
    player.durationChanged.connect(on_duration_changed)
    timeline.sliderPressed.connect(on_slider_pressed)
    timeline.sliderReleased.connect(on_slider_released)
    timeline.sliderMoved.connect(on_slider_moved)

    controls = QHBoxLayout()
    play_btn = QPushButton("⏸ Tạm dừng")
    play_btn.setStyleSheet(
        "QPushButton { background: #e8e8e8; color: #111; padding: 6px 14px;"
        " border: 1px solid #bbb; border-radius: 4px; }"
        "QPushButton:hover { background: #ddd; }"
    )

    def toggle_play():
        if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            player.pause()
            play_btn.setText("▶ Phát")
        else:
            player.play()
            play_btn.setText("⏸ Tạm dừng")

    play_btn.clicked.connect(toggle_play)
    controls.addWidget(play_btn)
    controls.addStretch()
    controls.addWidget(time_label)
    root_layout.addLayout(controls)
    root_layout.addWidget(timeline)

    hint = QLabel("Space: phát/dừng  •  Enter: tiếp tục  •  Esc: huỷ")
    hint.setStyleSheet("color: #888; font-size: 10px;")
    root_layout.addWidget(hint)

    action_row = QHBoxLayout()
    approve_btn = QPushButton("✓  Tiếp tục upload")
    approve_btn.setStyleSheet(
        "QPushButton { background: #27ae60; color: white; font-weight: bold;"
        " padding: 10px 12px; border: none; border-radius: 4px; }"
        "QPushButton:hover { background: #219a52; }"
    )
    cancel_btn = QPushButton("✕  Huỷ")
    cancel_btn.setStyleSheet(
        "QPushButton { background: #c0392b; color: white;"
        " padding: 10px 12px; border: none; border-radius: 4px; }"
        "QPushButton:hover { background: #a93226; }"
    )

    def approve():
        dialog.done(QDialog.DialogCode.Accepted)

    def cancel():
        dialog.done(QDialog.DialogCode.Rejected)

    approve_btn.clicked.connect(approve)
    cancel_btn.clicked.connect(cancel)
    action_row.addWidget(approve_btn)
    action_row.addWidget(cancel_btn)
    root_layout.addLayout(action_row)

    def on_key(event):
        if event.key() == Qt.Key.Key_Space:
            toggle_play()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            approve()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            cancel()
            event.accept()
        else:
            QDialog.keyPressEvent(dialog, event)

    dialog.keyPressEvent = on_key
    dialog.setStyleSheet("QDialog { background: #f0f0f0; }")

    player.play()
    result = dialog.exec() == QDialog.DialogCode.Accepted
    player.stop()
    return result


def confirm_video_preview(video_path, title=None):
    """
    Xem trước video nhúng trong cửa sổ (PyQt6 — giống thẻ <video> trên browser).

    Returns:
        True  — tiếp tục pipeline
        False — huỷ pipeline
    """
    if not os.path.isfile(video_path):
        print(f"❌ Không tìm thấy video preview: {video_path}")
        return False

    try:
        return _confirm_with_pyqt(video_path, title=title)
    except ImportError:
        print("ℹ️  PyQt6 chưa cài — fallback sang player ngoài. Cài: pip install PyQt6")
        return _confirm_with_external_player(video_path, title=title)
