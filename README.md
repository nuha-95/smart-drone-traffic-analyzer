# Smart Drone Traffic Analyzer

Smart Drone Traffic Analyzer is a full-stack web app for uploading drone footage, running vehicle detection and tracking, and returning:

- total vehicle count
- counts by vehicle type
- processed output video
- downloadable CSV report

The project uses:

- React frontend
- FastAPI backend
- SQLite for job tracking
- YOLOv8 for detection
- ByteTrack for tracking

## Table of Contents

- [Setup Options](#setup-options)
- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Run with Docker](#run-with-docker)
- [Run Locally](#run-locally)
- [Architecture](#architecture)
- [Tracking Methodology](#tracking-methodology)
- [Engineering Assumptions](#engineering-assumptions)
- [API Summary](#api-summary)

## Setup Options

Clone the repository:

```bash
git clone https://github.com/nuha-95/smart-drone-traffic-analyzer
```

Recommended order:

1. For the most reproducible setup, use Docker
2. For local development, use `setup.sh` and then `start.sh`
3. If needed, install dependencies manually and use `start.sh` or `start.bat`

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- Miniconda or Anaconda
- Docker and Docker Compose for containerized runs

Important runtime files:

- `backend/services/yolov8n.pt`
- `backend/services/bytetrack.yaml`

## Project Structure

```text
smart-drone-traffic-analyzer/
|-- backend/
|   |-- main.py
|   |-- api/routes.py
|   |-- models/database.py
|   `-- services/
|       |-- video_processor.py
|       |-- bytetrack.yaml
|       `-- yolov8n.pt
|-- frontend/
|   |-- src/
|   `-- package.json
|-- storage/
|   |-- uploads/
|   |-- outputs/
|   |-- reports/
|   `-- jobs.db
|-- docker-compose.yml
|-- requirements.txt
|-- setup.sh
|-- start.sh
|-- start.bat
`-- README.md
```

## Run with Docker

```bash
docker compose up --build 
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

Docker helps keep the runtime environment consistent across machines.

## Run Locally

Before running locally, install Miniconda or Anaconda and make sure `conda` is available in your shell.

## 1. Run setup

```bash
./setup.sh
```

`setup.sh` will:

- check that `conda` exists
- create `drone-env` if it does not exist
- install backend dependencies from `requirements.txt`
- install frontend dependencies
- create the storage folders

## 2. Start the app

Linux/macOS/Git Bash:

```bash
./start.sh
```

Windows:

```bat
start.bat
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Architecture

The app has two layers:

- React frontend for upload, progress, and results
- FastAPI backend for processing, persistence, and file serving

Frontend flow:

1. Upload video with `POST /upload`
2. Start processing with `POST /process/{job_id}`
3. Listen for progress over WebSocket and poll status as fallback
4. Load results, processed video, and CSV report after completion

Backend flow:

1. Save uploaded video under `storage/uploads/`
2. Create a job record in SQLite
3. Run background processing
4. Save processed video to `storage/outputs/`
5. Save CSV report to `storage/reports/`
6. Return status and result data through API endpoints

Concurrency model:

- FastAPI background tasks keep the API responsive during processing
- a dedicated frame-reader thread reads video frames into a queue
- WebSocket queues push live progress updates to the frontend

## Tracking Methodology

The system uses YOLOv8 + ByteTrack and counts vehicles with a horizontal line-crossing method.

How it works:

1. YOLOv8 detects vehicles in each processed frame
2. ByteTrack assigns persistent track IDs across frames
3. The app tracks each object's vertical center point
4. A vehicle is counted when its track crosses the center line

Supported vehicle classes:

- `car`
- `truck`
- `bus`
- `motorcycle`

How double-counting is handled:

- each tracked object has a `track_id`
- counted IDs are stored in a set
- once a track is counted, it is not counted again

Known edge-case handling:

- objects without stable track IDs are skipped
- vehicles that never cross the line are not counted
- if a vehicle lingers near the line, only the first valid crossing is counted

## Engineering Assumptions

- input files are `.mp4`
- `backend/services/yolov8n.pt` is present at runtime
- `backend/services/bytetrack.yaml` is present at runtime
- SQLite is sufficient for the current single-instance workflow
- preventing duplicate counts is more important than aggressively recovering every missed count

## API Summary

- `POST /upload` uploads a video and creates a job
- `POST /process/{job_id}` starts processing
- `GET /status/{job_id}` returns current status and progress
- `WS /ws/{job_id}` streams live progress
- `GET /result/{job_id}` returns final metrics
- `GET /video/{job_id}` returns the processed video
- `GET /download/{job_id}` downloads the CSV report
