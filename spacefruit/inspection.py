"""Stage-two plant health inspection workflow."""

from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime

from .models import PlantInspectionResult


class PlantHealthInspector:
    """Visits every planted profile and runs camera-based health inspection."""

    def __init__(self, navigator, camera, health_model):
        self.navigator = navigator
        self.camera = camera
        self.health_model = health_model

    def inspect_all(self, robot) -> None:
        planted_cells = [cell for cell in robot.planting_cells if cell.profile_id]
        total = len(planted_cells)

        robot.inspection_results = []
        robot.health_alerts = []

        for index, cell in enumerate(planted_cells, start=1):
            profile = robot.plant_profiles.get(cell.profile_id)
            if profile is None:
                continue

            robot.current_inspection_index = index - 1
            robot.message = (
                f"Inspecting plant {index}/{total}: {profile.plant_type} "
                f"({profile.profile_id})"
            )

            self.navigator.go_to(cell.x_m, cell.y_m)
            frame = self.camera.capture(cell.x_m, cell.y_m)
            detection = self.health_model.analyze(frame, profile.plant_type)

            inspected_at = datetime.now().astimezone().isoformat(timespec="seconds")
            result = PlantInspectionResult(
                inspection_id=f"INSPECT-{profile.profile_id}-{index}",
                profile_id=profile.profile_id,
                plant_type=profile.plant_type,
                inspected_at=inspected_at,
                x_m=cell.x_m,
                y_m=cell.y_m,
                condition=detection.condition,
                confidence=detection.confidence,
                disease_detected=detection.detected,
                notes=detection.notes,
            )
            robot.inspection_results.append(result)

            profile.last_inspected_at = inspected_at
            profile.last_inspection_id = result.inspection_id

            if detection.detected:
                profile.health_status = (
                    f"attention required: {detection.condition or 'unknown condition'}"
                )
                robot.health_alerts.append({
                    "profile_id": profile.profile_id,
                    "plant_type": profile.plant_type,
                    "condition": detection.condition or "unknown condition",
                    "confidence": detection.confidence,
                    "inspected_at": inspected_at,
                    "message": (
                        f"Possible plant health issue detected in "
                        f"{profile.plant_type} ({profile.profile_id})."
                    ),
                })
                print(
                    f"[ALERT] Possible issue: {profile.plant_type} "
                    f"({profile.profile_id}) -> {detection.condition}"
                )
            else:
                profile.health_status = "inspected"
                print(f"[VISION] {profile.plant_type} ({profile.profile_id}): no issue detected")

            robot.state_revision += 1
            time.sleep(0.05)

        robot.current_inspection_index = max(0, total - 1) if total else 0
        robot.state = robot.inspection_complete_state
        if robot.health_alerts:
            robot.message = (
                f"Inspection complete. {len(robot.health_alerts)} plant health "
                f"alert(s) require attention."
            )
        else:
            robot.message = (
                f"Inspection complete. {total} plant(s) inspected; "
                "no model alerts were returned."
            )
        robot.state_revision += 1
