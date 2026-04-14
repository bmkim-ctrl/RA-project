from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from services.inference import run_inference
from services.report import generate_report
from services.storage import storage


VALID_EXTENSIONS = {".png", ".jpg", ".jpeg"}
BASE_DIR = Path(__file__).resolve().parents[1]
IMAGE_ROOT = BASE_DIR / "images"
class ImageWatcher:
    def __init__(self) -> None:
        self._observer: PollingObserver | None = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        IMAGE_ROOT.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        if self._observer is not None:
            return
        self.reconcile_filesystem()
        handler = ImageFolderHandler(self)
        # PollingObserver is more stable on Windows/Conda/Python 3.13 than the native watcher backend.
        self._observer = PollingObserver(timeout=1.0)
        self._observer.schedule(handler, str(IMAGE_ROOT), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None

    def reconcile_filesystem(self) -> None:
        storage.reconcile_filesystem(IMAGE_ROOT, VALID_EXTENSIONS)
        for patient_dir in sorted(IMAGE_ROOT.iterdir()) if IMAGE_ROOT.exists() else []:
            if not patient_dir.is_dir():
                continue
            for image_path in sorted(patient_dir.iterdir()):
                if image_path.suffix.lower() not in VALID_EXTENSIONS:
                    continue
                storage.ensure_patient_image(patient_dir.name, image_path.name)
                patient = storage.get_patient(patient_dir.name)
                record = next((item for item in patient["images"] if item["filename"] == image_path.name), None)
                if record and not record.get("has_analysis"):
                    self.enqueue_image(image_path)

    def enqueue_image(self, image_path: Path) -> None:
        if image_path.suffix.lower() not in VALID_EXTENSIONS:
            return
        self._executor.submit(self._process_image, image_path)

    def _process_image(self, image_path: Path) -> None:
        patient_id = image_path.parent.name
        filename = image_path.name
        storage.ensure_patient_image(patient_id, filename)
        storage.mark_reading(patient_id, filename)
        storage.broadcast({"event": "new_image", "patient_id": patient_id, "filename": filename, "status": "READING"})

        time.sleep(0.15)
        inference = run_inference(str(image_path))
        report = generate_report(float(inference["confidence_score"]), str(inference["diagnosis"]))
        storage.save_inference(patient_id, filename, inference, report)
        storage.broadcast({"event": "analysis_complete", "patient_id": patient_id, "filename": filename, "status": "DONE"})


class ImageFolderHandler(FileSystemEventHandler):
    def __init__(self, watcher: ImageWatcher) -> None:
        self.watcher = watcher

    def on_created(self, event) -> None:
        self.watcher.reconcile_filesystem()
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in VALID_EXTENSIONS:
            return
        self.watcher.enqueue_image(path)

    def on_deleted(self, event) -> None:
        self.watcher.reconcile_filesystem()
        path = Path(event.src_path)
        if event.is_directory:
            storage.broadcast({"event": "patient_deleted", "patient_id": path.name, "status": None})
            return
        if path.suffix.lower() in VALID_EXTENSIONS:
            storage.broadcast({"event": "image_deleted", "patient_id": path.parent.name, "filename": path.name, "status": None})

    def on_moved(self, event) -> None:
        self.watcher.reconcile_filesystem()
        src = Path(event.src_path)
        dest = Path(event.dest_path)
        if event.is_directory:
            storage.broadcast({"event": "patient_deleted", "patient_id": src.name, "status": None})
            storage.broadcast({"event": "new_image", "patient_id": dest.name, "status": "NEW"})
            return
        if dest.suffix.lower() in VALID_EXTENSIONS:
            self.watcher.enqueue_image(dest)
            storage.broadcast({"event": "new_image", "patient_id": dest.parent.name, "filename": dest.name, "status": "NEW"})


watcher = ImageWatcher()
