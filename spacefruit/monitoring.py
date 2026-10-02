"""Monitoring workflow and swappable visual-model interfaces."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Protocol

from .models import PlantProfile, PlantingCell


@dataclass
class CameraFrame:
    cell_id: str
    image_path: Optional[str] = None
    captured: bool = False


@dataclass
class HealthAnalysis:
    issue_detected: bool
    issues: list[str]
    summary: str


@dataclass
class WeedAnalysis:
    weed_detected: bool
    weeds_found: int
    summary: str


class CameraSensor(Protocol):
    def capture(self, cell: PlantingCell) -> CameraFrame:
        ...


class VisualHealthModel(Protocol):
    def analyze(self, frame: CameraFrame, profile: PlantProfile) -> HealthAnalysis:
        ...


class VisualWeedModel(Protocol):
    def analyze(self, frame: CameraFrame, cell: PlantingCell) -> WeedAnalysis:
        ...


class CameraPlaceholder:
    """Camera interface placeholder; replace capture() with a real camera driver."""

    def capture(self, cell: PlantingCell) -> CameraFrame:
        return CameraFrame(
            cell_id=cell.profile_id or f"{cell.row}-{cell.column}",
            image_path=None,
            captured=False,
        )


class PlaceholderHealthModel:
    """Visual-model adapter placeholder for future CV/ML inference."""

    def analyze(self, frame: CameraFrame, profile: PlantProfile) -> HealthAnalysis:
        return HealthAnalysis(
            issue_detected=False,
            issues=[],
            summary="No visual health issue detected by placeholder model.",
        )


class PlaceholderWeedModel:
    """Visual weed-model adapter placeholder for future CV/ML inference."""

    def analyze(self, frame: CameraFrame, cell: PlantingCell) -> WeedAnalysis:
        return WeedAnalysis(
            weed_detected=False,
            weeds_found=0,
            summary="No weed detected by placeholder model.",
        )


class MonitoringWorkflow:
    """Drives to every planted cell, analyzes plant health, then removes detected weeds."""

    def __init__(
        self,
        robot,
        camera: Optional[CameraSensor] = None,
        health_model: Optional[VisualHealthModel] = None,
        weed_model: Optional[VisualWeedModel] = None,
    ):
        self.robot = robot
        self.camera = camera or CameraPlaceholder()
        self.health_model = health_model or PlaceholderHealthModel()
        self.weed_model = weed_model or PlaceholderWeedModel()

    def run(self) -> None:
        cells = [cell for cell in self.robot.planting_cells if cell.profile_id]
        total = len(cells)
        if total == 0:
            raise RuntimeError("MONITORING_NO_PLANTS: no planted plant profiles are available.")

        self.robot.state = self.robot.state.__class__.MONITORING
        self.robot.monitoring = {
            "running": True,
            "completed": 0,
            "total": total,
            "issues_detected": 0,
            "weeds_removed": 0,
            "current_profile_id": None,
            "last_health_result": None,
            "last_weed_result": None,
        }
        self.robot.message = f"Monitoring started: 0/{total} plants checked."

        for index, cell in enumerate(cells, start=1):
            profile = self.robot.plant_profiles.get(cell.profile_id)
            if profile is None:
                continue

            self.robot.monitoring["current_profile_id"] = profile.profile_id
            self.robot.message = f"Driving to plant {index}/{total}: {profile.plant_type}"
            self._drive_to(cell)
            frame = self.camera.capture(cell)

            health = self.health_model.analyze(frame, profile)
            self._apply_health_result(profile, health)
            self.robot.monitoring["last_health_result"] = {
                "profile_id": profile.profile_id,
                "issue_detected": health.issue_detected,
                "issues": health.issues,
                "summary": health.summary,
            }

            self.robot.message = f"Checking weeds at plant {index}/{total}: {profile.plant_type}"
            weed = self.weed_model.analyze(frame, cell)
            removed = self._remove_weeds(cell, weed)
            self.robot.monitoring["last_weed_result"] = {
                "profile_id": profile.profile_id,
                "weed_detected": weed.weed_detected,
                "weeds_found": weed.weeds_found,
                "removed": removed,
                "summary": weed.summary,
            }

            self.robot.monitoring["completed"] = index
            self.robot.monitoring["issues_detected"] += int(health.issue_detected)
            self.robot.monitoring["weeds_removed"] += removed
            self.robot.state_revision += 1

        self.robot.monitoring["running"] = False
        self.robot.monitoring["current_profile_id"] = None
        self.robot.message = (
            f"Monitoring complete: {total} plants checked, "
            f"{self.robot.monitoring['issues_detected']} health issues found, "
            f"{self.robot.monitoring['weeds_removed']} weeds removed."
        )
        self.robot.state = self.robot.state.__class__.COMPLETE
        self.robot.state_revision += 1

    def _drive_to(self, cell: PlantingCell) -> None:
        # Replace this delay with the real navigation/controller command.
        time.sleep(0.05)

    def _apply_health_result(self, profile: PlantProfile, result: HealthAnalysis) -> None:
        profile.last_monitored_at = self.robot.now_iso()
        profile.health_status = result.summary
        profile.health_issues = list(result.issues)
        profile.health_issue_detected = result.issue_detected

    def _remove_weeds(self, cell: PlantingCell, result: WeedAnalysis) -> int:
        if not result.weed_detected or result.weeds_found <= 0:
            cell.weeds_detected = 0
            cell.weeds_removed = 0
            return 0
        removed = self.robot.weed_remover.pluck(result.weeds_found, cell)
        cell.weeds_detected = result.weeds_found
        cell.weeds_removed = removed
        return removed
