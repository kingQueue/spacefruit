"""Core data models used by SpaceFruit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class GPSReading:
    latitude: float
    longitude: float
    accuracy_m: float


@dataclass
class EnvironmentReading:
    temperature_c: float
    humidity_percent: float


@dataclass
class Plot:
    width_m: float
    length_m: float
    origin_latitude: float
    origin_longitude: float
    boundary_points: list[tuple[float, float]]


@dataclass
class PlantCatalogEntry:
    name: str
    min_temp_c: float
    max_temp_c: float
    max_humidity_percent: float
    spacing_m: float
    planting_depth_m: float
    sunlight: str
    water_needs: str
    typical_germination_days: int
    preferred_months: set[int]


@dataclass
class PlantRecommendation:
    name: str
    reason: str
    spacing_m: float
    planting_depth_m: float


@dataclass
class PlantingCell:
    row: int
    column: int
    x_m: float
    y_m: float
    plant: str
    spacing_m: float
    planting_depth_m: float
    profile_id: Optional[str] = None
    status: str = "pending"
    seed_number: int = 0
    error: Optional[str] = None


class PlantingStepError(RuntimeError):
    """Raised when one seed fails a required planting workflow step."""
    def __init__(self, code: str, seed_number: int, plant: str, step: str, detail: str):
        self.code = code
        self.seed_number = seed_number
        self.plant = plant
        self.step = step
        self.detail = detail
        super().__init__(f"[{code}] Seed {seed_number} ({plant}) failed at {step}: {detail}")


@dataclass
class PlantProfile:
    profile_id: str
    img: str
    plant_type: str
    age_days: int
    planted_at: str
    x_m: float
    y_m: float
    spacing_m: float
    planting_depth_m: float
    temperature_at_planting_c: float
    humidity_at_planting_percent: float
    sunlight: str
    water_needs: str
    typical_germination_days: int
    health_status: str = "newly planted"
    health_issues: list[str] = None
    health_issue_detected: bool = False
    last_monitored_at: Optional[str] = None
    weeds_detected: int = 0
    weeds_removed: int = 0

    def __post_init__(self):
        if self.health_issues is None:
            self.health_issues = []


class RobotState(str, Enum):
    WAITING_FOR_START = "waiting_for_start"
    MAPPING = "mapping"
    RECOMMENDING = "recommending"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    WAITING_FOR_SEEDS = "waiting_for_seeds"
    PLANTING = "planting"
    COMPLETE = "complete"
    MONITORING = "monitoring"
    ERROR = "error"


