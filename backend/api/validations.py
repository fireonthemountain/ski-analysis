"""Assessment-validation API: submit ratings + media, poll, fetch the report."""
import json
import os
import shutil
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

import config
from api.users import get_current_user
from database import SessionLocal, User, ValidationRun, get_db
from database.models import ProcessingStatus
from pipeline import ingest
from pipeline.assessment import Assessment, catalog_json
from pipeline.runner import run_validation

router = APIRouter(prefix="/api/v1", tags=["validation"])

# One run at a time: pose estimation saturates the CPU, and a queue keeps the UI honest.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="validation")
_progress: dict[str, dict] = {}
_lock = threading.Lock()


def runs_root() -> str:
    path = os.path.join(config.DATA_DIR, "validations")
    os.makedirs(path, exist_ok=True)
    return path


def _set_progress(run_id: str, fraction: float, message: str) -> None:
    with _lock:
        _progress[run_id] = {"fraction": round(float(fraction), 3), "message": message}


def _process(run_id: str, media_paths: list[str]) -> None:
    db = SessionLocal()
    run = db.query(ValidationRun).filter(ValidationRun.id == uuid.UUID(run_id)).first()
    try:
        run.status = ProcessingStatus.PROCESSING
        db.commit()
        _set_progress(run_id, 0.02, "Starting")
        result = run_validation(
            Assessment(**run.assessment), media_paths, run.result_dir,
            progress=lambda f, m: _set_progress(run_id, f, m),
            target_fps=config.ANALYSIS_FPS, max_seconds=config.MAX_ANALYSIS_SECONDS,
            display_names=[os.path.basename(n or '') or f'file {i + 1}' for i, n in enumerate(run.media_files or [])],
        )
        run.summary = result["summary"]
        run.status = ProcessingStatus.COMPLETED
    except Exception as e:  # noqa: BLE001 - report any failure to the user rather than hang
        traceback.print_exc()
        run.status = ProcessingStatus.FAILED
        run.error = str(e) or e.__class__.__name__
    finally:
        run.finished_at = datetime.utcnow()
        db.commit()
        db.close()
        if media_paths:                      # the uploaded originals are not kept; only annotated outputs are
            shutil.rmtree(os.path.dirname(media_paths[0]), ignore_errors=True)
        with _lock:
            _progress.pop(run_id, None)


def fail_interrupted_runs() -> int:
    """On startup: runs left pending/processing by a previous process can never finish."""
    db = SessionLocal()
    try:
        stuck = db.query(ValidationRun).filter(
            ValidationRun.status.in_([ProcessingStatus.PENDING, ProcessingStatus.PROCESSING])).all()
        for r in stuck:
            r.status, r.error = ProcessingStatus.FAILED, "Interrupted: the server restarted while this run was processing."
        db.commit()
        return len(stuck)
    finally:
        db.close()


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _brief(run: ValidationRun) -> dict:
    return {"id": str(run.id), "status": run.status.value, "run_label": run.run_label, "media_kind": run.media_kind,
            "media_files": run.media_files, "created_at": _iso(run.created_at), "finished_at": _iso(run.finished_at),
            "summary": run.summary, "error": run.error, "items_assessed": len((run.assessment or {}).get("items", []))}


def _get_run(run_id: str, user: User, db: Session) -> ValidationRun:
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid validation id")
    run = db.query(ValidationRun).filter(ValidationRun.id == rid, ValidationRun.user_id == user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Validation not found")
    return run


@router.get("/assessment/catalog")
def get_catalog():
    """Everything the assessment form needs: items, rating options, thresholds, requirements."""
    return {"framework": "PSIA Alpine fundamentals", "items": catalog_json(),
            "limits": {"max_video_mb": config.MAX_VIDEO_SIZE_MB, "max_image_mb": config.MAX_IMAGE_SIZE_MB,
                       "max_images": config.MAX_IMAGES, "analysis_fps": config.ANALYSIS_FPS,
                       "max_analysis_seconds": config.MAX_ANALYSIS_SECONDS},
            "video_extensions": sorted(ingest.VIDEO_EXT), "image_extensions": sorted(ingest.IMAGE_EXT)}


@router.post("/validations", status_code=202)
def create_validation(assessment: str = Form(..., description="Assessment JSON"),
                      files: list[UploadFile] = File(..., description="One video OR one-or-more images"),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        parsed = Assessment(**json.loads(assessment))
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="assessment is not valid JSON")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=[{"loc": list(x["loc"]), "msg": x["msg"]} for x in e.errors()])

    kinds = [ingest.kind_of(f.filename or "") for f in files]
    if not files or None in kinds:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload one video (mp4/mov/m4v/avi/mkv/webm) or images (jpg/png/webp/heic).")
    if "video" in kinds and len(files) != 1:
        raise HTTPException(status_code=400, detail="Upload either ONE video or a set of still images, not a mix.")
    if len(files) > config.MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Too many images (max {config.MAX_IMAGES}).")
    is_video = kinds[0] == "video"
    limit = (config.MAX_VIDEO_SIZE_MB if is_video else config.MAX_IMAGE_SIZE_MB) * 1024 * 1024

    run_id = uuid.uuid4()
    result_dir = os.path.join(runs_root(), str(run_id))
    upload_dir = os.path.join(result_dir, "upload")
    os.makedirs(upload_dir)
    paths = []
    try:
        for i, f in enumerate(files):
            ext = os.path.splitext(f.filename or "")[1].lower()
            path = os.path.join(upload_dir, f"{i:03d}{ext}")       # never trust client file names on disk
            size = 0
            with open(path, "wb") as out:
                while chunk := f.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(status_code=413, detail=f"{f.filename} is larger than {limit // (1024 * 1024)} MB.")
                    out.write(chunk)
            paths.append(path)
    except HTTPException:
        shutil.rmtree(result_dir, ignore_errors=True)
        raise

    run = ValidationRun(id=run_id, user_id=user.id, status=ProcessingStatus.PENDING, run_label=parsed.run_label,
                        media_kind="video" if is_video else "images", media_files=[f.filename for f in files],
                        assessment=parsed.model_dump(), result_dir=result_dir)
    db.add(run)
    db.commit()
    _set_progress(str(run_id), 0.0, "Queued")
    _executor.submit(_process, str(run_id), paths)
    return {"id": str(run_id), "status": "pending", "user": user.username}


@router.get("/validations")
def list_validations(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(ValidationRun).filter(ValidationRun.user_id == user.id)
            .order_by(ValidationRun.created_at.desc()).limit(min(limit, 200)).all())
    return {"user": user.username, "validations": [_brief(r) for r in rows]}


@router.get("/validations/{run_id}")
def get_validation(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _get_run(run_id, user, db)
    out = _brief(run)
    out["assessment"] = run.assessment
    with _lock:
        out["progress"] = _progress.get(str(run.id))
    if run.status == ProcessingStatus.COMPLETED:
        path = os.path.join(run.result_dir, "result.json")
        if not os.path.exists(path):
            raise HTTPException(status_code=500, detail="Result file is missing on disk")
        with open(path) as fh:
            out["result"] = json.load(fh)
    return out


@router.get("/validations/{run_id}/files/{file_path:path}")
def get_validation_file(run_id: str, file_path: str, db: Session = Depends(get_db)):
    """Annotated frames / video. Addressed by unguessable run id so <img>/<video> tags can load them."""
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid validation id")
    run = db.query(ValidationRun).filter(ValidationRun.id == rid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Validation not found")
    root = os.path.realpath(run.result_dir)
    full = os.path.realpath(os.path.join(root, file_path))
    allowed = full.startswith(os.path.join(root, "frames") + os.sep) or full == os.path.join(root, "annotated.mp4")
    if not allowed or not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full)


@router.delete("/validations/{run_id}", status_code=204)
def delete_validation(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _get_run(run_id, user, db)
    if run.status in (ProcessingStatus.PENDING, ProcessingStatus.PROCESSING):
        raise HTTPException(status_code=409, detail="This run is still processing")
    shutil.rmtree(run.result_dir, ignore_errors=True)
    db.delete(run)
    db.commit()
