import uuid
import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.models.database import Job, SessionLocal, get_db
from backend.services.video_processor import process_video

router = APIRouter()
_STORAGE = Path(__file__).resolve().parents[2] / "storage"
UPLOAD_DIR = _STORAGE / "uploads"
OUTPUT_DIR = _STORAGE / "outputs"
REPORT_DIR = _STORAGE / "reports"

for directory in (UPLOAD_DIR, OUTPUT_DIR, REPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Registry: job_id -> (event loop, asyncio.Queue) for pushing progress to WebSocket
_ws_queues: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = {}


def _push_ws_message(job_id: str, message: dict):
    listener = _ws_queues.get(job_id)
    if not listener:
        return

    loop, q = listener
    try:
        loop.call_soon_threadsafe(q.put_nowait, message)
    except (RuntimeError, asyncio.QueueFull):
        pass


def _run_processing(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        job.status = "processing"
        job.progress = 0
        db.commit()

        output_video = str(OUTPUT_DIR / f"{job_id}.mp4")
        report = str(REPORT_DIR / f"{job_id}.csv")

        def update_progress(pct: int):
            job.progress = pct
            db.commit()
            _push_ws_message(job_id, {"status": "processing", "progress": pct})

        result = process_video(job.video_path, output_video, report, progress_cb=update_progress)

        job.status = "completed"
        job.progress = 100
        job.output_video_path = output_video
        job.report_path = report
        job.total_count = result["total_count"]
        job.processing_time = result["processing_time"]
        db.commit()

        _push_ws_message(job_id, {"status": "completed", "progress": 100})
    except Exception as e:
        db.rollback()
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = "failed"
            db.commit()
        _push_ws_message(job_id, {"status": "failed", "progress": 0})
        print(f"[ERROR] job {job_id}: {e}")
    finally:
        db.close()


@router.post("/upload")
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(400, "No file selected")
    if not filename.lower().endswith(".mp4"):
        raise HTTPException(400, "Only .mp4 files accepted")
    job_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{job_id}.mp4"
    dest.write_bytes(await file.read())
    job = Job(job_id=job_id, video_path=str(dest))
    db.add(job)
    db.commit()
    return {"job_id": job_id, "status": "uploaded"}


@router.post("/process/{job_id}")
def start_processing(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in ("uploaded", "failed"):
        raise HTTPException(400, f"Job already {job.status}")
    background_tasks.add_task(_run_processing, job_id)
    return {"job_id": job_id, "status": "queued"}


@router.get("/status/{job_id}")
def get_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return {"status": job.status, "progress": job.progress}


@router.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    db = SessionLocal()
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _ws_queues[job_id] = (asyncio.get_running_loop(), q)
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            await websocket.send_json({"status": "failed", "progress": 0})
            return

        await websocket.send_json({"status": job.status, "progress": job.progress})
        if job.status in ("completed", "failed"):
            return

        while True:
            msg = await q.get()
            await websocket.send_json(msg)
            if msg["status"] in ("completed", "failed"):
                break
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _ws_queues.pop(job_id, None)
        db.close()


@router.get("/result/{job_id}")
def get_result(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "completed":
        raise HTTPException(400, f"Job not completed: {job.status}")
    counts = {}
    if job.report_path and Path(job.report_path).exists():
        with open(job.report_path) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 2 and parts[0] in ("car", "truck", "bus", "motorcycle"):
                    counts[parts[0]] = int(parts[1])
    return {
        "total_count": job.total_count,
        "counts_by_type": counts,
        "processing_time": job.processing_time,
    }


@router.get("/download/{job_id}")
def download_report(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job or not job.report_path or not Path(job.report_path).exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(job.report_path, media_type="text/csv", filename=f"report_{job_id}.csv")


@router.get("/video/{job_id}")
def get_video(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job or not job.output_video_path or not Path(job.output_video_path).exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(
        job.output_video_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )
