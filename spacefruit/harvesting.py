"""Camera-guided simulated harvest checks and collection."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional, Protocol

from .hardware import Harvester
from .models import PlantProfile, PlantingCell, RobotState
from .monitoring import CameraFrame, CameraSensor, SimulatedCamera


@dataclass
class HarvestAnalysis:
    ready: bool
    summary: str


class VisualHarvestModel(Protocol):
    def analyze(self, frame: CameraFrame, profile: PlantProfile) -> HarvestAnalysis:
        ...


class SimulatedHarvestReadinessModel:
    """Fake camera inference that randomly decides whether a plant is ripe."""

    def __init__(self, rng=None, readiness_rate: float = 0.65):
        self.rng = rng or random.Random()
        self.readiness_rate = readiness_rate

    def analyze(self, frame: CameraFrame, profile: PlantProfile) -> HarvestAnalysis:
        if not frame.captured:
            return HarvestAnalysis(False, "Camera could not capture the plant; harvest was skipped.")
        if self.rng.random() < self.readiness_rate:
            return HarvestAnalysis(True, f"Camera confirms the {profile.plant_type} is ready to harvest.")
        return HarvestAnalysis(False, f"Camera says the {profile.plant_type} is not ready to harvest yet.")


class HarvestingWorkflow:
    """Drive to one selected plant, check ripeness, and collect it when ready."""

    def __init__(
        self,
        robot,
        camera: Optional[CameraSensor] = None,
        readiness_model: Optional[VisualHarvestModel] = None,
        harvester: Optional[Harvester] = None,
    ):
        self.robot = robot
        self.camera = camera or SimulatedCamera()
        self.readiness_model = readiness_model or SimulatedHarvestReadinessModel()
        self.harvester = harvester or robot.harvester

    def run(self, profile_id: str) -> HarvestAnalysis:
        profile = self.robot.plant_profiles.get(profile_id)
        if profile is None:
            raise ValueError("The selected plant profile was not found.")
        cell = next(
            (candidate for candidate in self.robot.planting_cells if candidate.profile_id == profile_id),
            None,
        )
        if cell is None or cell.status != "planted":
            raise ValueError("The selected plant is no longer available to harvest.")

        self.robot.message = f"Driving to {profile.plant_type} at ({cell.x_m:.2f}m, {cell.y_m:.2f}m) to check harvest readiness."
        time.sleep(0.05)
        frame = self.camera.capture(cell)
        result = self.readiness_model.analyze(frame, profile)

        profile.harvest_ready = result.ready
        profile.harvest_check_summary = result.summary
        profile.last_harvest_check_at = self.robot.now_iso()
        if not result.ready:
            profile.harvest_status = "not_ready"
            self.robot.message = result.summary
            self.robot.state = RobotState.COMPLETE
            self.robot.state_revision += 1
            return result

        self.robot.message = f"Harvesting {profile.plant_type} into robot inventory."
        if not self.harvester.harvest(profile, cell):
            raise RuntimeError(f"The harvester could not collect {profile.plant_type}.")

        harvested_at = self.robot.now_iso()
        profile.harvest_status = "harvested"
        profile.harvested_at = harvested_at
        cell.status = "harvested"
        self.robot.harvest_inventory[profile.plant_type] = (
            self.robot.harvest_inventory.get(profile.plant_type, 0) + 1
        )
        inventory_item = self.robot.harvest_inventory_items.setdefault(
            profile.plant_type,
            {"plant_type": profile.plant_type, "img": profile.img or "default.svg", "quantity": 0},
        )
        inventory_item["quantity"] += 1
        self.robot.harvested_items.append({
            "profile_id": profile.profile_id,
            "plant_type": profile.plant_type,
            "quantity": 1,
            "harvested_at": harvested_at,
        })
        self.robot.replace_with_empty_plot(cell, profile)
        self.robot.message = f"Harvested {profile.plant_type}. Added 1 to robot inventory."
        self.robot.state = RobotState.COMPLETE
        self.robot.state_revision += 1
        return result
