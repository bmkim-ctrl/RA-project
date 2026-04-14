from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


PatientStatus = Literal["NEW", "READING", "DONE"]


class AnalysisResult(BaseModel):
    detection_image: str
    gradcam_image: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    diagnosis: str


class ImageRecord(BaseModel):
    filename: str
    url: str
    has_analysis: bool
    confidence_score: float | None = None
    diagnosis: str | None = None
    detection_image: str | None = None
    gradcam_image: str | None = None
    report: str | None = None
    warning: str | None = None
    last_updated: str | None = None


class PatientSummary(BaseModel):
    patient_id: str
    image_count: int
    status: PatientStatus


class PatientDetail(BaseModel):
    patient_id: str
    status: PatientStatus
    images: list[ImageRecord]


class PatientsResponse(BaseModel):
    patients: list[PatientSummary]


class ReportRequest(BaseModel):
    filename: str


class SaveReadingRequest(BaseModel):
    filename: str
    diagnosis: str
    report: str


class ReportResponse(BaseModel):
    report: str
    truncated: bool = False
    warning: str | None = None


class SaveReadingResponse(BaseModel):
    message: str
