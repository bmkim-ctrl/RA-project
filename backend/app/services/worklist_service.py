from __future__ import annotations

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ..models.schemas import ImageRecord, PatientDetail, PatientSummary, ReportResponse
from .ai_model import get_model
from .gpt_service import get_gpt_service


VALID_EXTENSIONS = {".png", ".jpg", ".jpeg"}
BASE_DIR = Path(__file__).resolve().parents[3]
IMAGE_ROOT = BASE_DIR / "images"
RUNTIME_DIR = BASE_DIR / ".runtime"
CACHE_PATH = RUNTIME_DIR / "analysis_cache.json"


class WorklistService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: dict[str, dict[str, Any]] = {}
        self._connections: set[asyncio.Queue[dict[str, Any]]] = set()
        self._observer: Observer | None = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self._load_cache()

    def start(self) -> None:
        if self._observer is not None:
            return
        self._bootstrap_existing_files()
        handler = ImageEventHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(IMAGE_ROOT), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None

    def list_patients(self) -> list[PatientSummary]:
        patients: list[PatientSummary] = []
        for patient_dir in sorted(IMAGE_ROOT.iterdir()) if IMAGE_ROOT.exists() else []:
            if not patient_dir.is_dir():
                continue
            image_files = [file for file in sorted(patient_dir.iterdir()) if file.suffix.lower() in VALID_EXTENSIONS]
            if not image_files:
                continue
            patient_id = patient_dir.name
            patients.append(
                PatientSummary(
                    patient_id=patient_id,
                    image_count=len(image_files),
                    status=self._compute_patient_status(patient_id, image_files),
                )
            )
        return patients

    def get_patient_detail(self, patient_id: str) -> PatientDetail:
        patient_dir = IMAGE_ROOT / patient_id
        if not patient_dir.exists() or not patient_dir.is_dir():
            raise FileNotFoundError(patient_id)

        image_files = [file for file in sorted(patient_dir.iterdir()) if file.suffix.lower() in VALID_EXTENSIONS]
        images: list[ImageRecord] = []
        for image_file in image_files:
            key = self._cache_key(patient_id, image_file.name)
            cached = self._cache.get(key, {})
            images.append(
                ImageRecord(
                    filename=image_file.name,
                    url=f"/patients/{patient_id}/images/{image_file.name}",
                    has_analysis=bool(cached.get("analysis")),
                    confidence_score=cached.get("confidence_score"),
                    diagnosis=self._public_diagnosis(cached),
                    detection_image=cached.get("detection_image"),
                    gradcam_image=cached.get("gradcam_image"),
                    report=cached.get("report"),
                    warning=cached.get("warning"),
                    last_updated=cached.get("last_updated"),
                )
            )

        return PatientDetail(
            patient_id=patient_id,
            status=self._compute_patient_status(patient_id, image_files),
            images=images,
        )

    def get_image_path(self, patient_id: str, filename: str) -> Path:
        image_path = IMAGE_ROOT / patient_id / filename
        if not image_path.exists() or image_path.suffix.lower() not in VALID_EXTENSIONS:
            raise FileNotFoundError(filename)
        return image_path

    def save_reading(self, patient_id: str, filename: str, diagnosis: str, report: str) -> None:
        key = self._cache_key(patient_id, filename)
        with self._lock:
            cached = self._cache.setdefault(key, {})
            cached["diagnosis_override"] = diagnosis
            cached["report"] = report
            cached["last_updated"] = self._timestamp()
            self._persist_cache()
        self.broadcast({"event": "reading_saved", "patient_id": patient_id, "filename": filename, "status": "DONE"})

    def regenerate_report(self, patient_id: str, filename: str) -> ReportResponse:
        key = self._cache_key(patient_id, filename)
        with self._lock:
            cached = self._cache.get(key)
            if not cached:
                raise FileNotFoundError(key)
            diagnosis = cached.get("diagnosis_override") or cached.get("diagnosis") or "Pending review"
            result = get_gpt_service().generate_report(diagnosis, cached.get("confidence_score", 0.0), patient_id, filename)
            cached["report"] = result.report
            cached["warning"] = result.warning
            cached["last_updated"] = self._timestamp()
            self._persist_cache()
        return ReportResponse(report=result.report, truncated=result.truncated, warning=result.warning)

    def register_connection(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connections.add(queue)
        queue.put_nowait({"event": "bootstrap", "patient_id": "", "status": "NEW"})
        return queue

    def unregister_connection(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._connections.discard(queue)

    def broadcast(self, message: dict[str, Any]) -> None:
        for queue in list(self._connections):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                self._connections.discard(queue)

    def enqueue_file(self, file_path: Path) -> None:
        if file_path.suffix.lower() not in VALID_EXTENSIONS:
            return
        self._executor.submit(self._process_file, file_path)

    def _process_file(self, file_path: Path) -> None:
        patient_id = file_path.parent.name
        filename = file_path.name
        key = self._cache_key(patient_id, filename)

        with self._lock:
            current = self._cache.setdefault(key, {})
            current["processing"] = True
            current["last_updated"] = self._timestamp()
            self._persist_cache()
        self.broadcast({"event": "new_image", "patient_id": patient_id, "filename": filename, "status": "READING"})

        image_bytes = file_path.read_bytes()
        inference = get_model().infer(image_bytes)
        report_result = get_gpt_service().generate_report(inference.diagnosis, inference.confidence_score, patient_id, filename)

        with self._lock:
            cached = self._cache.setdefault(key, {})
            cached.update(
                {
                    "analysis": True,
                    "processing": False,
                    "detection_image": inference.detection_image,
                    "gradcam_image": inference.gradcam_image,
                    "confidence_score": inference.confidence_score,
                    "diagnosis": inference.diagnosis,
                    "report": report_result.report,
                    "warning": report_result.warning,
                    "last_updated": self._timestamp(),
                }
            )
            self._persist_cache()

        self.broadcast({"event": "analysis_complete", "patient_id": patient_id, "filename": filename, "status": "DONE"})

    def _bootstrap_existing_files(self) -> None:
        for patient_dir in sorted(IMAGE_ROOT.iterdir()) if IMAGE_ROOT.exists() else []:
            if not patient_dir.is_dir():
                continue
            for file_path in sorted(patient_dir.iterdir()):
                if file_path.suffix.lower() not in VALID_EXTENSIONS:
                    continue
                key = self._cache_key(patient_dir.name, file_path.name)
                cached = self._cache.get(key)
                if cached and cached.get("analysis") and not cached.get("processing"):
                    continue
                self.enqueue_file(file_path)

    def _compute_patient_status(self, patient_id: str, image_files: list[Path]) -> str:
        statuses: list[str] = []
        for file_path in image_files:
            cached = self._cache.get(self._cache_key(patient_id, file_path.name), {})
            if cached.get("processing"):
                statuses.append("READING")
            elif cached.get("analysis"):
                statuses.append("DONE")
            else:
                statuses.append("NEW")
        if "READING" in statuses:
            return "READING"
        if statuses and all(status == "DONE" for status in statuses):
            return "DONE"
        return "NEW"

    def _public_diagnosis(self, cached: dict[str, Any]) -> str | None:
        confidence = cached.get("confidence_score")
        if confidence is None or confidence < 0.3:
            return None
        return cached.get("diagnosis_override") or cached.get("diagnosis")

    def _load_cache(self) -> None:
        if not CACHE_PATH.exists():
            return
        try:
            self._cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._cache = {}

    def _persist_cache(self) -> None:
        CACHE_PATH.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False), encoding="utf-8")

    def _cache_key(self, patient_id: str, filename: str) -> str:
        return f"{patient_id}/{filename}"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class ImageEventHandler(FileSystemEventHandler):
    def __init__(self, service: WorklistService) -> None:
        self.service = service

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        time.sleep(0.1)
        self.service.enqueue_file(Path(event.src_path))


worklist_service = WorklistService()
