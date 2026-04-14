from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from ..models.schemas import PatientsResponse, ReportRequest, SaveReadingRequest, SaveReadingResponse
from ..services.worklist_service import worklist_service


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ra-worklist"}


@router.get("/patients", response_model=PatientsResponse)
async def list_patients() -> PatientsResponse:
    return PatientsResponse(patients=worklist_service.list_patients())


@router.get("/patients/{patient_id}")
async def patient_detail(patient_id: str):
    try:
        return worklist_service.get_patient_detail(patient_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Patient not found: {exc}") from exc


@router.get("/patients/{patient_id}/images/{filename}")
async def get_image(patient_id: str, filename: str):
    try:
        return FileResponse(worklist_service.get_image_path(patient_id, filename))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Image not found: {exc}") from exc


@router.post("/patients/{patient_id}/reading", response_model=SaveReadingResponse)
async def save_reading(patient_id: str, payload: SaveReadingRequest) -> SaveReadingResponse:
    try:
        worklist_service.get_image_path(patient_id, payload.filename)
        worklist_service.save_reading(patient_id, payload.filename, payload.diagnosis, payload.report)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Image not found: {exc}") from exc
    return SaveReadingResponse(message="Reading saved")


@router.post("/patients/{patient_id}/report/generate")
async def generate_report(patient_id: str, payload: ReportRequest):
    try:
        worklist_service.get_image_path(patient_id, payload.filename)
        return worklist_service.regenerate_report(patient_id, payload.filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {exc}") from exc


@router.websocket("/ws")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    queue = worklist_service.register_connection()
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        worklist_service.unregister_connection(queue)
