import cv2
import csv
import time
import queue
import threading
import subprocess
from pathlib import Path
from ultralytics import YOLO
import imageio_ffmpeg

VEHICLE_CLASSES   = {"car", "truck", "bus", "motorcycle"}
FRAME_SKIP        = 2
RESIZE_WIDTH      = 640
PROGRESS_INTERVAL = 10

CLASS_COLORS = {
    "car":        (0, 255, 0),
    "truck":      (0, 0, 255),
    "bus":        (255, 165, 0),
    "motorcycle": (255, 0, 255),
}

DOWN = "down"
UP   = "up"

_TRACKER_CFG = Path(__file__).resolve().parent / "bytetrack.yaml"


def _get_direction(prev_y: float, curr_y: float, line_y: int):
    """Returns crossing direction or None if no crossing."""
    if prev_y < line_y <= curr_y:
        return DOWN
    if curr_y < line_y <= prev_y:
        return UP
    return None


def _frame_reader(cap: cv2.VideoCapture, q: queue.Queue, frame_skip: int):
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            q.put((None, None))
            break
        idx += 1
        if idx % frame_skip == 0:
            q.put((idx, frame))


def process_video(video_path: str, output_video_path: str, report_path: str, progress_cb=None):
    model = YOLO(Path(__file__).resolve().parent / "yolov8n.pt")
    model.fuse()
    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    vehicle_class_ids = [idx for idx, name in model.names.items() if name in VEHICLE_CLASSES]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    orig_w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps          = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out_fps      = fps / FRAME_SKIP

    frame_w = RESIZE_WIDTH
    frame_h = int(orig_h * (RESIZE_WIDTH / orig_w))
    line_y  = int(frame_h * 0.5)

    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_proc = subprocess.Popen([
        ffmpeg_exe, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{frame_w}x{frame_h}",
        "-pix_fmt", "bgr24", "-r", str(out_fps),
        "-i", "pipe:0",
        "-vcodec", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "28",
        output_video_path
    ], stdin=subprocess.PIPE)

    # ── Async frame reader ────────────────────────────────────────────────────
    frame_queue = queue.Queue(maxsize=16)
    reader_thread = threading.Thread(
        target=_frame_reader, args=(cap, frame_queue, FRAME_SKIP), daemon=True
    )
    reader_thread.start()

    # ── State ─────────────────────────────────────────────────────────────────
    counted_ids:     set  = set()
    track_prev:      dict = {}   # track_id -> prev_cy
    track_direction: dict = {}   # track_id -> confirmed direction once counted
    vehicle_records: list = []
    counts:          dict = {c: 0 for c in VEHICLE_CLASSES}
    dir_counts             = {DOWN: 0, UP: 0}

    processed  = 0
    start_time = time.time()

    while True:
        frame_idx, frame = frame_queue.get()
        if frame_idx is None:
            break

        frame = cv2.resize(frame, (frame_w, frame_h))
        results = model.track(
            frame,
            persist=True,
            verbose=False,
            classes=vehicle_class_ids,
            imgsz=frame_w,
            device=device,
            half=(device == "cuda"),
            conf=0.25,
            tracker=str(_TRACKER_CFG),
        )

        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                if box.id is None:
                    continue
                track_id = int(box.id.item())
                cls_name = model.names[int(box.cls.item())]
                if cls_name not in VEHICLE_CLASSES:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cy = (y1 + y2) // 2

                if track_id in track_prev:
                    prev_cy = track_prev[track_id]
                    direction = _get_direction(prev_cy, cy, line_y)

                    if direction and track_id not in counted_ids:
                        counted_ids.add(track_id)
                        counts[cls_name] += 1
                        dir_counts[direction] += 1
                        track_direction[track_id] = direction
                        vehicle_records.append({
                            "vehicle_id":       track_id,
                            "vehicle_type":     cls_name,
                            "timestamp":        round(frame_idx / fps, 2),
                        })

                track_prev[track_id] = cy

                color = CLASS_COLORS.get(cls_name, (255, 255, 255))
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{cls_name} ID:{track_id}"
                if track_id in track_direction:
                    direction_text = "DOWN" if track_direction[track_id] == DOWN else "UP"
                    label = f"{label} {direction_text}"
                cv2.putText(frame, label, (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # ── Overlays ──────────────────────────────────────────────────────────
        cv2.line(frame, (0, line_y), (frame_w, line_y), (0, 0, 255), 2)
        cv2.putText(frame, f"Total: {len(counted_ids)}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        ffmpeg_proc.stdin.write(frame.tobytes())

        processed += 1
        if progress_cb and total_frames > 0 and processed % PROGRESS_INTERVAL == 0:
            pct = min(int((frame_idx / total_frames) * 90), 90)
            progress_cb(pct)

    # ── Cleanup ────────────────────────────────────────────────────────────────
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    cap.release()
    reader_thread.join()

    processing_time = round(time.time() - start_time, 2)

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", newline="") as f:
        writer_csv = csv.DictWriter(
            f, fieldnames=["vehicle_id", "vehicle_type", "timestamp"]
        )
        writer_csv.writeheader()
        writer_csv.writerows(vehicle_records)
        f.write("\n")
        f.write(f"total_count,{len(counted_ids)}\n")
        f.write(f"down_count,{dir_counts[DOWN]}\n")
        f.write(f"up_count,{dir_counts[UP]}\n")
        f.write(f"processing_duration_sec,{processing_time}\n")
        for cls, cnt in counts.items():
            f.write(f"{cls},{cnt}\n")

    return {
        "total_count":     len(counted_ids),
        "counts":          counts,
        "dir_counts":      dir_counts,
        "processing_time": processing_time,
    }
