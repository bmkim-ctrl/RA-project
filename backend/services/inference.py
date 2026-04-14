from __future__ import annotations

import random
from hashlib import sha256
from urllib.parse import quote


DIAGNOSES = ["positive", "negative", "uncertain"]


def _svg_data_uri(svg: str) -> str:
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def _detection_overlay(seed: int) -> str:
    rng = random.Random(seed)
    x = 22 + rng.randint(0, 24)
    y = 26 + rng.randint(0, 26)
    width = 20 + rng.randint(0, 10)
    height = 18 + rng.randint(0, 12)
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      <rect x="{x}" y="{y}" width="{width}" height="{height}"
            fill="none" stroke="#ff3b30" stroke-width="3" rx="2" />
    </svg>
    """
    return _svg_data_uri(" ".join(svg.split()))


def _gradcam_overlay(seed: int) -> str:
    rng = random.Random(seed + 17)
    cx = 30 + rng.randint(0, 18)
    cy = 30 + rng.randint(0, 18)
    radius = 12 + rng.randint(0, 6)
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      <defs>
        <radialGradient id="heat">
          <stop offset="0%" stop-color="rgba(255,0,0,0.85)" />
          <stop offset="100%" stop-color="rgba(255,0,0,0.18)" />
        </radialGradient>
      </defs>
      <circle cx="{cx}" cy="{cy}" r="{radius}" fill="url(#heat)" />
    </svg>
    """
    return _svg_data_uri(" ".join(svg.split()))


def _confidence(seed: int) -> float:
    return round(0.24 + ((seed % 66) / 100), 2)


def run_inference(image_path: str) -> dict[str, object]:
    digest = sha256(image_path.encode("utf-8")).hexdigest()
    seed = int(digest[:8], 16)
    confidence = min(_confidence(seed), 0.92)
    diagnosis = DIAGNOSES[seed % len(DIAGNOSES)]

    return {
        "detection_image": _detection_overlay(seed),
        "gradcam_image": _gradcam_overlay(seed),
        "confidence_score": confidence,
        "diagnosis": diagnosis,
    }
