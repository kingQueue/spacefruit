"""Farming robot workflow orchestration."""

from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from .catalog import CATALOG_BY_NAME, PLANT_CATALOG
from .hardware import GPSSensor, Planter, PlotMapper, StartButton, TemperatureHumiditySensor
from .models import EnvironmentReading, GPSReading, PlantProfile, PlantRecommendation, PlantingCell, PlantingStepError, Plot, RobotState
from .planner import GridPlanner
from .recommendations import PlantRecommendationEngine
from .web import APP_HOST, APP_PORT, THUMBS_DIR, AppServer, render_app

class FarmingRobot:
    def __init__(self, start_server: bool = True, app_host: str = APP_HOST, app_port: int = APP_PORT):
        self.state = RobotState.WAITING_FOR_START
        self.start_button = StartButton()
        self.env_sensor = TemperatureHumiditySensor()
        self.gps_sensor = GPSSensor()
        self.mapper = PlotMapper(DEMO_PLOT_WIDTH_M, DEMO_PLOT_LENGTH_M)
        self.recommender = PlantRecommendationEngine()
        self.grid_planner = GridPlanner()
        self.planter = Planter()

        self.environment: Optional[EnvironmentReading] = None
        self.gps: Optional[GPSReading] = None
        self.plot: Optional[Plot] = None
        self.recommendations: list[PlantRecommendation] = []

        # User-editable plan: plant type -> exact number of seeds to plant.
        self.seed_plan: dict[str, int] = {}
        self.planting_cells: list[PlantingCell] = []
        self.plant_profiles: dict[str, PlantProfile] = {}
        self.loaded_seed_counts: dict[str, int] = {}
        self.planting_errors: list[str] = []
        self.last_error: Optional[str] = None
        self.planted_counts: dict[str, int] = {}

        self.confirmed = False
        self.current_cell_index = 0
        self.state_revision = 0
        self.message = "Waiting for start button."
        self.app_server = AppServer(self, app_host, app_port) if start_server else None

    # ----------------------------
    # Planning edits
    # ----------------------------

    def add_plant_to_plan(self, plant_name: Optional[str], count: int = 1) -> dict:
        if self.state != RobotState.WAITING_FOR_CONFIRMATION:
            return {"ok": False, "error": "The planting plan is no longer editable."}
        if plant_name not in CATALOG_BY_NAME:
            return {"ok": False, "error": "Unknown plant type."}
        count = int(count)
        if count < 1 or count > 1000:
            return {"ok": False, "error": "Seed count must be between 1 and 1000."}
        self.seed_plan[plant_name] = self.seed_plan.get(plant_name, 0) + count
        self.message = f"Planting plan updated: {self.total_requested_seeds()} seeds."
        return {"ok": True, "seed_plan": self.seed_plan}

    def remove_one_plant_from_plan(self, plant_name: Optional[str]) -> dict:
        if self.state != RobotState.WAITING_FOR_CONFIRMATION:
            return {"ok": False, "error": "The planting plan is no longer editable."}
        if plant_name not in self.seed_plan:
            return {"ok": False, "error": "Plant type is not in the current plan."}
        self.seed_plan[plant_name] -= 1
        if self.seed_plan[plant_name] <= 0:
            del self.seed_plan[plant_name]
        self.message = f"Planting plan updated: {self.total_requested_seeds()} seeds."
        return {"ok": True, "seed_plan": self.seed_plan}

    def total_requested_seeds(self) -> int:
        return sum(self.seed_plan.values())

    # ----------------------------
    # Seed loading
    # ----------------------------

    def load_seeds(self, counts: dict) -> dict:
        if self.state != RobotState.WAITING_FOR_SEEDS:
            return {"ok": False, "error": "The robot is not waiting for seeds."}

        normalized = {}
        for plant_name, requested in self.seed_plan.items():
            try:
                loaded = int(counts.get(plant_name, 0))
            except (TypeError, ValueError):
                return {"ok": False, "error": f"Invalid seed count for {plant_name}."}
            if loaded != requested:
                return {
                    "ok": False,
                    "error": (
                        f"{plant_name}: robot needs exactly {requested} seeds, "
                        f"but received {loaded}."
                    ),
                }
            normalized[plant_name] = loaded

        self.loaded_seed_counts = normalized
        self.planter.load_seeds(normalized)
        self.message = f"Verified {self.planter.seed_count} seeds. Planting can begin."
        print(f"[APP] Verified exact seed load: {self.loaded_seed_counts}")
        return {"ok": True, "loaded": self.loaded_seed_counts}

    # ----------------------------
    # Robot workflow
    # ----------------------------

    def run(self):
        if self.app_server is None:
            raise RuntimeError("APP_SERVER_DISABLED: FarmingRobot.run requires start_server=True.")
        self.app_server.start()
        try:
            self.wait_for_start()
            self.map_plot()
            self.collect_environment()
            self.make_recommendations()
            print(f"\n[APP] Open http://{APP_HOST}:{APP_PORT} to edit the planting plan.")
            self.wait_until_confirmed()
            self.create_planting_plan()
            print(f"\n[APP] Load the exact seed counts shown at http://{APP_HOST}:{APP_PORT}")
            self.wait_until_seeds_loaded()
            self.plant_all()
            self.state = RobotState.COMPLETE
            self.message = "Planting sequence complete. Plant profiles are ready."
            self.state_revision += 1
            print("\n[ROBOT] Planting sequence complete. Plant profiles created.")
        except KeyboardInterrupt:
            self.state = RobotState.ERROR
            self.message = "Stopped by user."
            print("\n[ROBOT] Stopped.")
        except Exception as exc:
            self.state = RobotState.ERROR
            self.last_error = str(exc)
            self.message = str(exc)
            if str(exc) not in self.planting_errors:
                self.planting_errors.append(str(exc))
            print(f"\n[ERROR] {exc}")

    def wait_for_start(self):
        self.state = RobotState.WAITING_FOR_START
        self.message = "Waiting for physical start button."
        self.start_button.wait_for_press()

    def map_plot(self):
        self.state = RobotState.MAPPING
        self.message = "Mapping plot."
        self.gps = self.gps_sensor.read()
        print(
            f"[GPS] Origin: lat={self.gps.latitude:.5f}, "
            f"lon={self.gps.longitude:.5f}, accuracy={self.gps.accuracy_m:.1f}m"
        )
        self.plot = self.mapper.map_plot(self.gps)
        print(f"[MAPPER] Plot mapped: {self.plot.width_m:.1f}m x {self.plot.length_m:.1f}m")

    def collect_environment(self):
        self.environment = self.env_sensor.read()
        print(f"[SENSOR] Temperature: {self.environment.temperature_c:.1f}°C")
        print(f"[SENSOR] Humidity: {self.environment.humidity_percent:.1f}%")

    def make_recommendations(self):
        self.state = RobotState.RECOMMENDING
        self.message = "Generating plant recommendations."
        assert self.environment is not None and self.gps is not None
        self.recommendations = self.recommender.recommend(
            self.environment, self.gps, datetime.now()
        )
        # Default to one seed of each recommended plant, which the user can edit.
        self.seed_plan = {item.name: 1 for item in self.recommendations[:5]}
        print("\n[RECOMMENDER] Suggested plants:")
        for recommendation in self.recommendations:
            print(f"  - {recommendation.name}: spacing={recommendation.spacing_m:.2f}m, depth={recommendation.planting_depth_m:.3f}m")
        self.state = RobotState.WAITING_FOR_CONFIRMATION
        self.message = "Edit the planting plan and confirm it in the app."

    def wait_until_confirmed(self):
        while not self.confirmed:
            time.sleep(0.25)

    def confirm_plan(self) -> dict:
        if self.state != RobotState.WAITING_FOR_CONFIRMATION:
            return {"ok": False, "error": "The plan cannot be confirmed in the current state."}
        if self.total_requested_seeds() <= 0:
            return {"ok": False, "error": "Add at least one seed before confirming."}
        self.confirmed = True
        self.state = RobotState.WAITING_FOR_SEEDS
        self.message = "Plan confirmed. Load the exact seed counts into the planter funnel."
        print(f"[APP] User confirmed {self.seed_plan}.")
        return {"ok": True, "state": self.state.value}

    def create_planting_plan(self):
        assert self.plot is not None
        self.planting_cells = self.grid_planner.create_grid(self.plot, self.seed_plan)
        self.message = (
            f"Created {len(self.planting_cells)} physical planting slots "
            f"from {len(self.seed_plan)} plant types."
        )
        print(f"[GRID] Created exactly {len(self.planting_cells)} planting slots.")

    def wait_until_seeds_loaded(self):
        while self.planter.seed_count < self.total_requested_seeds():
            time.sleep(0.25)

    def validate_planting_plan(self) -> None:
        requested_total = self.total_requested_seeds()
        if len(self.planting_cells) != requested_total:
            raise PlantingStepError("GRID_COUNT_MISMATCH", 0, "multiple", "grid_validation", f"expected {requested_total} planting slots but found {len(self.planting_cells)}")
        counts = {plant: 0 for plant in self.seed_plan}
        for cell in self.planting_cells:
            if cell.plant not in counts:
                raise PlantingStepError("GRID_UNKNOWN_PLANT", 0, cell.plant, "grid_validation", "plant type is not present in the confirmed seed plan")
            counts[cell.plant] += 1
        for plant, requested in self.seed_plan.items():
            if counts.get(plant, 0) != requested:
                raise PlantingStepError("GRID_PLANT_COUNT_MISMATCH", 0, plant, "grid_validation", f"expected {requested} slots but found {counts.get(plant, 0)}")

    def validate_planting_complete(self) -> None:
        for cell in self.planting_cells:
            if cell.status != "planted":
                raise PlantingStepError("PLANTING_INCOMPLETE", cell.seed_number, cell.plant, "completion_validation", f"cell is still {cell.status}")
            if not cell.profile_id or cell.profile_id not in self.plant_profiles:
                raise PlantingStepError("PROFILE_LINK_MISSING", cell.seed_number, cell.plant, "completion_validation", "planted cell has no valid profile link")
        if len(self.plant_profiles) != len(self.planting_cells):
            raise PlantingStepError("PROFILE_COUNT_MISMATCH", 0, "multiple", "completion_validation", f"expected {len(self.planting_cells)} profiles but found {len(self.plant_profiles)}")
        for plant, requested in self.seed_plan.items():
            if self.planted_counts.get(plant, 0) != requested:
                raise PlantingStepError("PLANTED_COUNT_MISMATCH", 0, plant, "completion_validation", f"expected {requested} planted seeds but recorded {self.planted_counts.get(plant, 0)}")
        if self.planter.seed_count != 0:
            raise PlantingStepError("SEED_INVENTORY_REMAINS", 0, "multiple", "completion_validation", f"{self.planter.seed_count} loaded seeds remain")

    def plant_all(self):
        self.state = RobotState.PLANTING
        self.current_cell_index = 0
        self.planted_counts = {plant: 0 for plant in self.seed_plan}
        self.validate_planting_plan()
        total = len(self.planting_cells)
        for index, cell in enumerate(self.planting_cells, start=1):
            self.current_cell_index = index - 1
            cell.seed_number = index
            cell.error = None
            self.message = f"Planting seed {index}/{total}: {cell.plant}"
            if cell.status != "pending":
                raise PlantingStepError("CELL_NOT_PENDING", index, cell.plant, "cell_validation", f"cell is already {cell.status}")
            before = self.planter.seed_inventory.get(cell.plant, 0)
            if before <= 0:
                error = PlantingStepError("SEED_INVENTORY_EMPTY", index, cell.plant, "seed_dispense", "no seed is available for this plant type")
                cell.error = str(error); self.planting_errors.append(str(error)); self.last_error = str(error); raise error
            try:
                planted = self.planter.plant(cell)
            except Exception as exc:
                error = PlantingStepError("PLANTER_EXCEPTION", index, cell.plant, "seed_dispense", str(exc))
                cell.error = str(error); self.planting_errors.append(str(error)); self.last_error = str(error); raise error from exc
            after = self.planter.seed_inventory.get(cell.plant, 0)
            if not planted or after != before - 1:
                error = PlantingStepError("SEED_DISPENSE_FAILED", index, cell.plant, "seed_dispense", f"expected inventory {before - 1}, got {after}")
                cell.error = str(error); self.planting_errors.append(str(error)); self.last_error = str(error); raise error
            cell.status = "planted"
            try:
                self.create_profile_for_cell(cell)
            except Exception as exc:
                cell.status = "error"
                error = PlantingStepError("PROFILE_CREATION_FAILED", index, cell.plant, "profile_creation", str(exc))
                cell.error = str(error); self.planting_errors.append(str(error)); self.last_error = str(error); raise error from exc
            if not cell.profile_id or cell.profile_id not in self.plant_profiles:
                cell.status = "error"
                error = PlantingStepError("PROFILE_LINK_FAILED", index, cell.plant, "profile_link", "profile was not stored and linked")
                cell.error = str(error); self.planting_errors.append(str(error)); self.last_error = str(error); raise error
            profile = self.plant_profiles[cell.profile_id]
            if profile.plant_type != cell.plant:
                cell.status = "error"
                error = PlantingStepError("PROFILE_PLANT_MISMATCH", index, cell.plant, "profile_validation", f"profile says {profile.plant_type!r}")
                cell.error = str(error); self.planting_errors.append(str(error)); self.last_error = str(error); raise error
            self.planted_counts[cell.plant] += 1
            self.state_revision += 1
            print(f"[ROBOT] Seed {index}/{total} completed: {cell.plant}")
        self.validate_planting_complete()
    @staticmethod
    def _normalize_plant_name(value: str) -> str:
        stem = os.path.splitext(os.path.basename(value))[0]
        return re.sub(r"[\s_-]+", " ", stem).strip().lower()

    def add_profile_img(self, plant: str) -> str:
        if not os.path.isdir(THUMBS_DIR):
            raise FileNotFoundError(f"THUMBNAIL_DIRECTORY_MISSING: {THUMBS_DIR}")
        matches = []
        for root, _, files in os.walk(THUMBS_DIR):
            for filename in files:
                if filename.startswith("_") or os.path.splitext(filename)[1].lower() not in {".svg", ".png", ".webp", ".jpg", ".jpeg"}:
                    continue
                if self._normalize_plant_name(filename) == self._normalize_plant_name(plant):
                    relative = os.path.relpath(os.path.join(root, filename), THUMBS_DIR)
                    matches.append(relative.replace(os.sep, "/"))
        if not matches:
            default_path = os.path.join(THUMBS_DIR, "default.svg")
            if not os.path.isfile(default_path):
                raise FileNotFoundError(f"THUMBNAIL_MISSING: no thumbnail found for {plant!r} and default.svg is missing")
            return "default.svg"
        priority = {".svg": 0, ".png": 1, ".webp": 2, ".jpg": 3, ".jpeg": 4}
        matches.sort(key=lambda name: (priority.get(os.path.splitext(name)[1].lower(), 99), name))
        return matches[0]
    def create_profile_for_cell(self, cell: PlantingCell):
        assert self.environment is not None
        catalog = CATALOG_BY_NAME[cell.plant]
        profile_id = f"PLANT-{uuid.uuid4().hex[:8].upper()}"
        planted_at = datetime.now().astimezone().isoformat(timespec="seconds")
        profile = PlantProfile(
            profile_id=profile_id,
            img=self.add_profile_img(cell.plant),
            plant_type=cell.plant,
            age_days=0,
            planted_at=planted_at,
            x_m=cell.x_m,
            y_m=cell.y_m,
            spacing_m=cell.spacing_m,
            planting_depth_m=cell.planting_depth_m,
            temperature_at_planting_c=self.environment.temperature_c,
            humidity_at_planting_percent=self.environment.humidity_percent,
            sunlight=catalog.sunlight,
            water_needs=catalog.water_needs,
            typical_germination_days=catalog.typical_germination_days,
        )
        if not profile.img:
            raise FileNotFoundError(f"THUMBNAIL_MISSING: no thumbnail resolved for {cell.plant}")
        self.plant_profiles[profile_id] = profile
        cell.profile_id = profile_id

    # ----------------------------
    # Visualization / API
    # ----------------------------

    def api_state(self) -> dict:
        catalog = [
            {
                **asdict(item),
                "preferred_months": sorted(item.preferred_months),
            }
            for item in PLANT_CATALOG
        ]
        return {
            "state": self.state.value,
            "message": self.message,
            "confirmed": self.confirmed,
            "environment": asdict(self.environment) if self.environment else None,
            "gps": asdict(self.gps) if self.gps else None,
            "plot": asdict(self.plot) if self.plot else None,
            "recommendations": [asdict(item) for item in self.recommendations],
            "seed_plan": self.seed_plan,
            "loaded_seed_counts": self.loaded_seed_counts,
            "planting_cells": [asdict(item) for item in self.planting_cells],
            "plant_profiles": [asdict(item) for item in self.plant_profiles.values()],
            "catalog": catalog,
            "seed_count": self.planter.seed_count,
            "total_requested_seeds": self.total_requested_seeds(),
            "current_cell_index": self.current_cell_index,
            "state_revision": self.state_revision,
            "planting_errors": self.planting_errors,
            "last_error": self.last_error,
            "planted_counts": self.planted_counts,
        }

