from __future__ import annotations

import asyncio
import json
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = BASE_DIR / ".runtime"
CACHE_FILE = RUNTIME_DIR / "patients_cache.json"


class PatientStorage:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._connections: set[asyncio.Queue[dict[str, Any]]] = set()
        self._patients: dict[str, dict[str, Any]] = {}
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self._load_cache()

    def list_patients(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "patient_id": patient_id,
                    "image_count": len(patient["images"]),
                    "status": patient["status"],
                }
                for patient_id, patient in sorted(self._patients.items())
            ]

    def reconcile_filesystem(self, image_root: Path, valid_extensions: set[str]) -> None:
        actual: dict[str, set[str]] = {}

        if image_root.exists():
            for patient_dir in sorted(image_root.iterdir()):
                if not patient_dir.is_dir():
                    continue
                filenames = {
                    file.name
                    for file in patient_dir.iterdir()
                    if file.is_file() and file.suffix.lower() in valid_extensions
                }
                if filenames:
                    actual[patient_dir.name] = filenames

        with self._lock:
            stale_patients = [patient_id for patient_id in self._patients if patient_id not in actual]
            for patient_id in stale_patients:
                self._patients.pop(patient_id, None)

            for patient_id, patient in list(self._patients.items()):
                if patient_id not in actual:
                    continue
                stale_images = [filename for filename in patient["images"] if filename not in actual[patient_id]]
                for filename in stale_images:
                    patient["images"].pop(filename, None)
                if patient["images"]:
                    self._refresh_status(patient_id)
                else:
                    self._patients.pop(patient_id, None)

            for patient_id, filenames in actual.items():
                patient = self._patients.setdefault(patient_id, {"patient_id": patient_id, "status": "NEW", "images": {}})
                for filename in filenames:
                    patient["images"].setdefault(
                        filename,
                        {
                            "filename": filename,
                            "has_analysis": False,
                            "processing": False,
                            "detection_image": None,
                            "gradcam_image": None,
                            "confidence_score": None,
                            "diagnosis": None,
                            "report": "",
                            "warning": None,
                            "updated_at": None,
                        },
                    )
                self._refresh_status(patient_id)

            self._persist()

    def get_patient(self, patient_id: str) -> dict[str, Any]:
        with self._lock:
            if patient_id not in self._patients:
                raise KeyError(patient_id)
            patient = deepcopy(self._patients[patient_id])
            patient["images"] = sorted(patient["images"].values(), key=lambda item: item["filename"])
            for image in patient["images"]:
                image["url"] = f"/patients/{patient_id}/images/{image['filename']}"
                confidence = image.get("confidence_score") or 0
                if confidence < 0.3:
                    image["diagnosis"] = None
            return patient

    def ensure_patient_image(self, patient_id: str, filename: str) -> None:
        with self._lock:
            patient = self._patients.setdefault(patient_id, {"patient_id": patient_id, "status": "NEW", "images": {}})
            patient["images"].setdefault(
                filename,
                {
                    "filename": filename,
                    "has_analysis": False,
                    "processing": False,
                    "detection_image": None,
                    "gradcam_image": None,
                    "confidence_score": None,
                    "diagnosis": None,
                    "report": "",
                    "warning": None,
                    "updated_at": None,
                },
            )
            self._refresh_status(patient_id)
            self._persist()

    def mark_reading(self, patient_id: str, filename: str) -> None:
        with self._lock:
            self.ensure_patient_image(patient_id, filename)
            record = self._patients[patient_id]["images"][filename]
            record["processing"] = True
            record["updated_at"] = self._timestamp()
            self._refresh_status(patient_id)
            self._persist()

    def save_inference(self, patient_id: str, filename: str, result: dict[str, Any], report: str) -> None:
        with self._lock:
            self.ensure_patient_image(patient_id, filename)
            record = self._patients[patient_id]["images"][filename]
            record.update(
                {
                    "has_analysis": True,
                    "processing": False,
                    "detection_image": result["detection_image"],
                    "gradcam_image": result["gradcam_image"],
                    "confidence_score": result["confidence_score"],
                    "diagnosis": result["diagnosis"],
                    "report": report,
                    "warning": "limited confidence" if float(result["confidence_score"]) < 0.5 else None,
                    "updated_at": self._timestamp(),
                }
            )
            self._refresh_status(patient_id)
            self._persist()

    def save_reading(self, patient_id: str, filename: str, diagnosis: str, report: str) -> None:
        with self._lock:
            record = self._patients[patient_id]["images"][filename]
            record["diagnosis"] = diagnosis
            record["report"] = report
            record["updated_at"] = self._timestamp()
            self._refresh_status(patient_id)
            self._persist()

    def update_report(self, patient_id: str, filename: str, report: str) -> dict[str, Any]:
        with self._lock:
            record = self._patients[patient_id]["images"][filename]
            record["report"] = report
            record["updated_at"] = self._timestamp()
            self._persist()
            return {"report": report, "warning": record["warning"]}

    def remove_image(self, patient_id: str, filename: str) -> bool:
        with self._lock:
            patient = self._patients.get(patient_id)
            if not patient:
                return False

            removed = patient["images"].pop(filename, None)
            if removed is None:
                return False

            if patient["images"]:
                self._refresh_status(patient_id)
            else:
                self._patients.pop(patient_id, None)

            self._persist()
            return True

    def remove_patient(self, patient_id: str) -> bool:
        with self._lock:
            removed = self._patients.pop(patient_id, None)
            if removed is None:
                return False
            self._persist()
            return True

    def register_connection(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connections.add(queue)
        queue.put_nowait({"event": "bootstrap", "patient_id": "", "status": None})
        return queue

    def unregister_connection(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._connections.discard(queue)

    def broadcast(self, payload: dict[str, Any]) -> None:
        for queue in list(self._connections):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                self._connections.discard(queue)

    def _refresh_status(self, patient_id: str) -> None:
        patient = self._patients[patient_id]
        images = list(patient["images"].values())
        if any(image["processing"] for image in images):
            patient["status"] = "READING"
        elif images and all(image["has_analysis"] for image in images):
            patient["status"] = "DONE"
        else:
            patient["status"] = "NEW"

    def _load_cache(self) -> None:
        if not CACHE_FILE.exists():
            return
        try:
            self._patients = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._patients = {}

    def _persist(self) -> None:
        CACHE_FILE.write_text(json.dumps(self._patients, indent=2, ensure_ascii=False), encoding="utf-8")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()


storage = PatientStorage()
