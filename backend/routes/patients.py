from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.report import generate_report as build_report
from services.storage import storage
from watcher import IMAGE_ROOT, VALID_EXTENSIONS


router = APIRouter(tags=["patients"])


class SaveReadingPayload(BaseModel):
    filename: str
    diagnosis: str
    report: str


class GenerateReportPayload(BaseModel):
    filename: str


@router.get("/patients")
async def list_patients() -> dict[str, object]:
    storage.reconcile_filesystem(IMAGE_ROOT, VALID_EXTENSIONS)
    return {"patients": storage.list_patients()}


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str) -> dict[str, object]:
    try:
        storage.reconcile_filesystem(IMAGE_ROOT, VALID_EXTENSIONS)
        return storage.get_patient(patient_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Patient not found: {patient_id}") from exc


@router.get("/patients/{patient_id}/images/{filename}")
async def serve_image(patient_id: str, filename: str):
    image_path = Path(__file__).resolve().parents[2] / "images" / patient_id / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
    return FileResponse(image_path)


@router.post("/patients/{patient_id}/report/generate")
async def generate_report(patient_id: str, payload: GenerateReportPayload) -> dict[str, object]:
    try:
        patient = storage.get_patient(patient_id)
        image = next(item for item in patient["images"] if item["filename"] == payload.filename)
        confidence = float(image.get("confidence_score") or 0)
        diagnosis = str(image.get("diagnosis") or "uncertain")
        report = build_report(confidence, diagnosis)
        return storage.update_report(patient_id, payload.filename, report)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc


@router.post("/patients/{patient_id}/reading")
async def save_reading(patient_id: str, payload: SaveReadingPayload) -> dict[str, str]:
    try:
        storage.save_reading(patient_id, payload.filename, payload.diagnosis, payload.report)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
    return {"message": "saved"}
