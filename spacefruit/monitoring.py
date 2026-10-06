"""Monitoring workflow and swappable visual-model interfaces."""

from __future__ import annotations

import time
import random
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


class SimulatedCamera:
    """Fake camera that returns a captured frame for each robot location."""

    def capture(self, cell: PlantingCell) -> CameraFrame:
        return CameraFrame(
            cell_id=cell.profile_id or f"{cell.row}-{cell.column}",
            image_path=f"simulated://camera/{cell.profile_id or cell.row}",
            captured=True,
        )


class SimulatedHealthModel:
    """Fake camera inference that flags one or two plants during each scan."""

    ISSUE_TYPES = ("possible malnutrition", "possible root rot")

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self._issues_by_profile: dict[str, list[str]] = {}

    def prepare_scan(self, profiles: list[PlantProfile]) -> None:
        """Choose a repeatable target set for this scan (one or two if available)."""
        self._issues_by_profile = {}
        if not profiles:
            return
        issue_count = self.rng.randint(1, min(2, len(profiles)))
        for profile in self.rng.sample(profiles, issue_count):
            self._issues_by_profile[profile.profile_id] = [self.rng.choice(self.ISSUE_TYPES)]

    def analyze(self, frame: CameraFrame, profile: PlantProfile) -> HealthAnalysis:
        issues = self._issues_by_profile.get(profile.profile_id, []) if frame.captured else []
        if issues:
            return HealthAnalysis(
                issue_detected=True,
                issues=list(issues),
                summary=f"Camera detected {', '.join(issues)}.",
            )
        return HealthAnalysis(
            issue_detected=False,
            issues=[],
            summary="Camera scan found no visible health issue.",
        )


class SimulatedWeedModel:
    """Fake camera inference that sometimes finds weeds around a plant."""

    def __init__(self, rng=None, detection_rate: float = 0.35):
        self.rng = rng or random.Random()
        self.detection_rate = detection_rate

    def analyze(self, frame: CameraFrame, cell: PlantingCell) -> WeedAnalysis:
        if frame.captured and self.rng.random() < self.detection_rate:
            weeds_found = self.rng.randint(1, 2)
            return WeedAnalysis(True, weeds_found, f"Camera detected {weeds_found} weed(s).")
        return WeedAnalysis(
            weed_detected=False,
            weeds_found=0,
            summary="Camera scan found no weeds.",
        )


# Backward-compatible names for callers that used the original placeholders.
CameraPlaceholder = SimulatedCamera
PlaceholderHealthModel = SimulatedHealthModel
PlaceholderWeedModel = SimulatedWeedModel


class MonitoringWorkflow:
    """Visits every planted cell, weeds it, then checks the plant's health."""

    def __init__(
        self,
        robot,
        camera: Optional[CameraSensor] = None,
        health_model: Optional[VisualHealthModel] = None,
        weed_model: Optional[VisualWeedModel] = None,
    ):
        self.robot = robot
        self.camera = camera or SimulatedCamera()
        self.health_model = health_model or SimulatedHealthModel()
        self.weed_model = weed_model or SimulatedWeedModel()

    def run(self) -> None:
        cells = [
            cell for cell in self.robot.planting_cells
            if cell.status == "planted"
            and cell.profile_id
            and cell.profile_id in self.robot.plant_profiles
        ]
        total = len(cells)
        if total == 0:
            raise RuntimeError("MONITORING_NO_PLANTS: no planted plant profiles are available.")

        self.robot.state = self.robot.state.__class__.MONITORING
        self.robot.monitoring = {
            "running": True,
            "completed": 0,
            "total": total,
            "issues_detected": 0,
            "alerts": [],
            "weeds_removed": 0,
            "weeding_completed": 0,
            "weeding_total": total,
            "weeding_percent": 0,
            "current_profile_id": None,
            "last_health_result": None,
            "last_weed_result": None,
        }
        self.robot.message = f"Monitoring started: 0/{total} plants checked."

        prepare_scan = getattr(self.health_model, "prepare_scan", None)
        if prepare_scan is not None:
            prepare_scan([self.robot.plant_profiles[cell.profile_id] for cell in cells])

        for index, cell in enumerate(cells, start=1):
            profile = self.robot.plant_profiles.get(cell.profile_id)
            if profile is None:
                continue

            self.robot.monitoring["current_profile_id"] = profile.profile_id
            self.robot.message = f"Driving to plant {index}/{total}: {profile.plant_type}"
            self._drive_to(cell)
            frame = self.camera.capture(cell)

            self.robot.message = f"Weeding location {index}/{total}: {profile.plant_type}"
            weed = self.weed_model.analyze(frame, cell)
            removed = self._remove_weeds(cell, weed)
            cell.weeding_completed = True
            self.robot.monitoring["weeding_completed"] = index
            self.robot.monitoring["weeding_percent"] = round(index * 100 / total)
            self.robot.monitoring["last_weed_result"] = {
                "profile_id": profile.profile_id,
                "weed_detected": weed.weed_detected,
                "weeds_found": weed.weeds_found,
                "removed": removed,
                "summary": weed.summary,
            }

            self.robot.message = f"Monitoring plant {index}/{total}: {profile.plant_type}"
            health = self.health_model.analyze(frame, profile)
            self._apply_health_result(profile, health)
            self.robot.monitoring["last_health_result"] = {
                "profile_id": profile.profile_id,
                "issue_detected": health.issue_detected,
                "issues": health.issues,
                "summary": health.summary,
            }
            if health.issue_detected:
                self.robot.monitoring["alerts"].append({
                    "profile_id": profile.profile_id,
                    "plant_type": profile.plant_type,
                    "issues": list(health.issues),
                    "message": f"Camera alert: {profile.plant_type} — {', '.join(health.issues)}.",
                    "detected_at": self.robot.now_iso(),
                })

            self.robot.monitoring["completed"] = index
            self.robot.monitoring["issues_detected"] += int(health.issue_detected)
            self.robot.monitoring["weeds_removed"] += removed
            self.robot.state_revision += 1

        self.robot.monitoring["running"] = False
        self.robot.monitoring["current_profile_id"] = None
        self.robot.message = (
            f"Monitoring complete: {total} plants checked, "
            f"weeding completed at {self.robot.monitoring['weeding_completed']}/{total} locations, "
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
