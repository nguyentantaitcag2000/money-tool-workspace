import os
import shutil
import subprocess
import tkinter as tk

try:
    import cv2
    from PIL import Image, ImageTk
except ImportError:
    cv2 = None
    Image = None
    ImageTk = None


def _start_audio_player(video_path):
    ffplay = shutil.which("ffplay")
    if not ffplay:
        return None
    return subprocess.Popen(
        [
            ffplay,
            "-nodisp",
            "-autoexit",
            "-loop", "0",
            video_path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_player(player):
    if player is None or player.poll() is not None:
        return
    player.terminate()
    try:
        player.wait(timeout=3)
    except subprocess.TimeoutExpired:
        player.kill()


def confirm_video_preview(video_path, title=None):
    """
    Hiển thị cửa sổ xem trước video với nút Next / Cancel.

    Returns:
        True  — tiếp tục pipeline
        False — huỷ pipeline
    """
    if not os.path.isfile(video_path):
        print(f"❌ Không tìm thấy video preview: {video_path}")
        return False

    if cv2 is None or Image is None or ImageTk is None:
        print(
            "❌ Thiếu opencv-python hoặc Pillow — không thể mở preview.\n"
            "   Cài đặt: pip install -r requirements.txt"
        )
        return False

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Không mở được video: {video_path}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_delay_ms = max(1, int(1000 / fps))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    max_w, max_h = 720, 960
    scale = min(max_w / src_w, max_h / src_h, 1.0)
    disp_w = max(1, int(src_w * scale))
    disp_h = max(1, int(src_h * scale))

    result = {"approved": False}
    state = {"running": True, "photo": None}
    audio_player = _start_audio_player(video_path)

    root = tk.Tk()
    root.title("Xem trước video")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    header = title or os.path.basename(video_path)
    tk.Label(root, text=header, font=("", 14, "bold"), wraplength=disp_w).pack(
        padx=12, pady=(12, 4)
    )
    tk.Label(root, text=os.path.basename(video_path), fg="gray").pack(pady=(0, 8))

    canvas = tk.Canvas(root, width=disp_w, height=disp_h, bg="black", highlightthickness=0)
    canvas.pack(padx=12)

    tk.Label(
        root,
        text="Xem video rồi chọn Next để upload hoặc Cancel để dừng.",
        wraplength=disp_w,
    ).pack(pady=(8, 4))

    def approve():
        result["approved"] = True
        state["running"] = False
        root.quit()
        root.destroy()

    def cancel():
        result["approved"] = False
        state["running"] = False
        root.quit()
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=(4, 12))
    tk.Button(btn_frame, text="Next", width=14, command=approve).pack(side=tk.LEFT, padx=8)
    tk.Button(btn_frame, text="Cancel", width=14, command=cancel).pack(side=tk.LEFT, padx=8)

    root.protocol("WM_DELETE_WINDOW", cancel)

    def show_frame():
        if not state["running"]:
            return

        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                root.after(frame_delay_ms, show_frame)
                return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if scale < 1.0:
            frame = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_AREA)

        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image=image)
        state["photo"] = photo
        canvas.delete("all")
        canvas.create_image(disp_w // 2, disp_h // 2, image=photo)
        root.after(frame_delay_ms, show_frame)

    show_frame()
    root.mainloop()

    cap.release()
    _stop_player(audio_player)
    return result["approved"]
