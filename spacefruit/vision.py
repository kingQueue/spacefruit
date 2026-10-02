"""Camera and computer-vision interfaces for plant health inspection.

The placeholder implementations let the robot run today while keeping the
hardware/model boundary ready for a real camera and ML model later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class CameraFrame:
    """A captured plant image plus metadata needed by a future CV pipeline."""
    captured_at: str
    x_m: float
    y_m: float
    image: Any = None


@dataclass
class DiseaseDetection:
    """Result returned by a plant-health computer vision model."""
    detected: bool
    condition: Optional[str] = None
    confidence: float = 0.0
    notes: str = ""


class PlantCamera:
    """Interface for the physical camera mounted on the farm robot."""

    def capture(self, x_m: float, y_m: float) -> CameraFrame:
        raise NotImplementedError


class PlaceholderCamera(PlantCamera):
    """Simulation camera.

    Replace this with an ESP32-CAM, USB camera, Raspberry Pi camera, etc.
    The returned frame deliberately contains no image data yet.
    """

    def capture(self, x_m: float, y_m: float) -> CameraFrame:
        print(f"[CAMERA] Capturing plant image at ({x_m:.2f}m, {y_m:.2f}m)")
        return CameraFrame(
            captured_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            x_m=x_m,
            y_m=y_m,
            image=None,
        )


class PlantHealthModel:
    """Interface for a future computer-vision disease classifier."""

    def analyze(self, frame: CameraFrame, plant_type: str) -> DiseaseDetection:
        raise NotImplementedError


class PlaceholderPlantHealthModel(PlantHealthModel):
    """Safe placeholder until a real disease model is connected.

    It does not claim to diagnose disease. It simply marks the inspection as
    pending/model-unavailable so the robot's inspection workflow can be tested.
    """

    def analyze(self, frame: CameraFrame, plant_type: str) -> DiseaseDetection:
        return DiseaseDetection(
            detected=False,
            condition=None,
            confidence=0.0,
            notes="Computer-vision model not connected; inspection placeholder only.",
        )
