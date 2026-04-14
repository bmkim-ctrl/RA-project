from __future__ import annotations

import base64
import random
from dataclasses import dataclass
from hashlib import sha256


DIAGNOSES = [
    "No active erosive change",
    "Mild synovitis pattern",
    "Suspicious erosive change",
    "Inflammatory arthritis pattern",
]


@dataclass
class MockInferenceResult:
    detection_image: str
    gradcam_image: str
    confidence_score: float
    diagnosis: str


class MockRAInferenceModel:
    def infer(self, image_bytes: bytes) -> MockInferenceResult:
        seed = int(sha256(image_bytes).hexdigest()[:8], 16)
        diagnosis = DIAGNOSES[seed % len(DIAGNOSES)]
        confidence = round(0.22 + (seed % 65) / 100, 2)
        return MockInferenceResult(
            detection_image=self._to_data_url(image_bytes),
            gradcam_image=self._to_data_url(image_bytes),
            confidence_score=min(confidence, 0.95),
            diagnosis=diagnosis,
        )

    def _to_data_url(self, image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:image/png;base64,{encoded}"


_model = MockRAInferenceModel()


def get_model() -> MockRAInferenceModel:
    return _model
