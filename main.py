"""
SpaceFruit Farming Robot - Python Demo

Simulation-first prototype for a Raspberry Pi farming robot.

Workflow:
1. Wait for the user start button.
2. Establish robot origin as (0, 0).
3. Simulate mapping a rectangular plot.
4. Read temperature, humidity, GPS and date.
5. Recommend plants from a 40-plant catalog.
6. Let the user add/remove individual crop types and set seed quantities.
7. Confirm the edited plan in the local app.
8. Build a physical planting grid containing exactly one slot per seed.
9. Ask the user to load the exact seed counts by plant type.
10. Simulate planting each seed.
11. Create a profile for every planted seed/plant.
12. Visualize the finished grid; each slot links to its plant profile.

Run:
    python3 main.py

Then open:
    http://127.0.0.1:8080

Press ENTER in the terminal to simulate the physical START button.
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import urlparse, unquote
import mimetypes
import re
import os


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_HOST = "127.0.0.1"
APP_PORT = 8080
THUMBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumbs")
DEMO_PLOT_WIDTH_M = 6.0
DEMO_PLOT_LENGTH_M = 8.0


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


class RobotState(str, Enum):
    WAITING_FOR_START = "waiting_for_start"
    MAPPING = "mapping"
    RECOMMENDING = "recommending"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    WAITING_FOR_SEEDS = "waiting_for_seeds"
    PLANTING = "planting"
    COMPLETE = "complete"
    ERROR = "error"


# ---------------------------------------------------------------------------
# 40-plant catalog
# ---------------------------------------------------------------------------

# These are demo agronomic defaults, not professional growing instructions.
# A production robot should source local extension/agronomy data and soil,
# weather, hardiness-zone and crop-variety information.

PLANT_CATALOG: list[PlantCatalogEntry] = [
    PlantCatalogEntry("Tomato", 18, 32, 85, 0.60, 0.02, "full sun", "medium", 7, {3,4,5,6,7}),
    PlantCatalogEntry("Bush Bean", 16, 30, 90, 0.20, 0.04, "full sun", "medium", 7, {4,5,6,7,8}),
    PlantCatalogEntry("Lettuce", 7, 24, 90, 0.25, 0.01, "partial to full sun", "medium", 7, {2,3,4,9,10,11}),
    PlantCatalogEntry("Radish", 8, 25, 95, 0.10, 0.015, "full sun to partial shade", "medium", 5, {2,3,4,9,10,11}),
    PlantCatalogEntry("Cucumber", 18, 32, 90, 0.45, 0.02, "full sun", "high", 5, {4,5,6,7}),
    PlantCatalogEntry("Carrot", 10, 27, 95, 0.08, 0.01, "full sun to partial shade", "medium", 10, {2,3,4,8,9,10}),
    PlantCatalogEntry("Spinach", 5, 23, 95, 0.15, 0.015, "partial shade to full sun", "medium", 7, {2,3,4,9,10,11}),
    PlantCatalogEntry("Kale", 7, 27, 95, 0.35, 0.015, "full sun to partial shade", "medium", 7, {2,3,4,8,9,10}),
    PlantCatalogEntry("Broccoli", 10, 24, 90, 0.45, 0.015, "full sun", "medium", 7, {2,3,4,7,8,9}),
    PlantCatalogEntry("Cauliflower", 10, 24, 90, 0.45, 0.01, "full sun", "medium", 7, {2,3,4,7,8,9}),
    PlantCatalogEntry("Cabbage", 7, 24, 90, 0.45, 0.01, "full sun", "medium", 7, {2,3,4,7,8,9}),
    PlantCatalogEntry("Bell Pepper", 18, 32, 85, 0.45, 0.01, "full sun", "medium", 10, {4,5,6,7}),
    PlantCatalogEntry("Jalapeno", 18, 32, 85, 0.45, 0.01, "full sun", "medium", 10, {4,5,6,7}),
    PlantCatalogEntry("Sweet Potato", 18, 32, 90, 0.35, 0.03, "full sun", "medium", 14, {4,5,6}),
    PlantCatalogEntry("Potato", 10, 27, 90, 0.30, 0.08, "full sun", "medium", 14, {2,3,4,8,9}),
    PlantCatalogEntry("Onion", 10, 27, 90, 0.10, 0.01, "full sun", "medium", 10, {2,3,4,8,9,10}),
    PlantCatalogEntry("Garlic", 5, 24, 90, 0.15, 0.05, "full sun", "medium", 14, {9,10,11}),
    PlantCatalogEntry("Beet", 10, 27, 95, 0.10, 0.02, "full sun to partial shade", "medium", 7, {2,3,4,8,9,10}),
    PlantCatalogEntry("Pea", 7, 24, 90, 0.08, 0.04, "full sun", "medium", 7, {2,3,4,8,9,10}),
    PlantCatalogEntry("Corn", 16, 32, 85, 0.25, 0.04, "full sun", "high", 7, {4,5,6}),
    PlantCatalogEntry("Zucchini", 18, 32, 90, 0.90, 0.02, "full sun", "high", 5, {4,5,6,7}),
    PlantCatalogEntry("Pumpkin", 18, 32, 90, 1.20, 0.03, "full sun", "high", 7, {4,5,6}),
    PlantCatalogEntry("Watermelon", 21, 35, 90, 1.20, 0.025, "full sun", "high", 7, {4,5,6}),
    PlantCatalogEntry("Cantaloupe", 21, 35, 90, 0.90, 0.025, "full sun", "high", 7, {4,5,6}),
    PlantCatalogEntry("Strawberry", 10, 27, 90, 0.30, 0.005, "full sun", "medium", 14, {3,4,5,9,10}),
    PlantCatalogEntry("Basil", 18, 32, 90, 0.25, 0.005, "full sun", "medium", 7, {4,5,6,7}),
    PlantCatalogEntry("Cilantro", 10, 27, 90, 0.15, 0.01, "partial shade to full sun", "medium", 7, {2,3,4,9,10,11}),
    PlantCatalogEntry("Parsley", 10, 27, 90, 0.20, 0.01, "partial shade to full sun", "medium", 14, {2,3,4,9,10,11}),
    PlantCatalogEntry("Dill", 13, 27, 90, 0.20, 0.01, "full sun", "medium", 10, {3,4,5,6,7,8}),
    PlantCatalogEntry("Mint", 10, 30, 90, 0.35, 0.005, "partial shade to full sun", "high", 10, {3,4,5,6,7,8}),
    PlantCatalogEntry("Thyme", 10, 30, 80, 0.30, 0.005, "full sun", "low", 14, {3,4,5,6,7,8}),
    PlantCatalogEntry("Oregano", 13, 30, 80, 0.30, 0.005, "full sun", "low", 10, {3,4,5,6,7,8}),
    PlantCatalogEntry("Rosemary", 15, 32, 80, 0.60, 0.005, "full sun", "low", 21, {3,4,5,6,7,8}),
    PlantCatalogEntry("Sage", 13, 30, 80, 0.45, 0.005, "full sun", "low", 14, {3,4,5,6,7,8}),
    PlantCatalogEntry("Eggplant", 18, 32, 85, 0.60, 0.01, "full sun", "medium", 10, {4,5,6,7}),
    PlantCatalogEntry("Turnip", 7, 27, 95, 0.10, 0.01, "full sun to partial shade", "medium", 5, {2,3,4,8,9,10,11}),
    PlantCatalogEntry("Swiss Chard", 7, 27, 95, 0.25, 0.015, "partial shade to full sun", "medium", 7, {2,3,4,8,9,10,11}),
    PlantCatalogEntry("Arugula", 7, 27, 95, 0.10, 0.01, "full sun to partial shade", "medium", 5, {2,3,4,9,10,11}),
    PlantCatalogEntry("Okra", 21, 35, 85, 0.45, 0.025, "full sun", "medium", 7, {4,5,6,7}),
    PlantCatalogEntry("Brussels Sprouts", 10, 24, 90, 0.60, 0.015, "full sun", "medium", 7, {2,3,4,7,8,9}),
    PlantCatalogEntry("Collard Greens", 7, 27, 95, 0.45, 0.015, "full sun to partial shade", "medium", 7, {2,3,4,8,9,10,11}),
]

CATALOG_BY_NAME = {plant.name: plant for plant in PLANT_CATALOG}


# ---------------------------------------------------------------------------
# Hardware simulation
# ---------------------------------------------------------------------------

class StartButton:
    def wait_for_press(self) -> None:
        input("\n[BUTTON] Press ENTER to simulate the physical START button... ")
        print("[BUTTON] Start detected.")


class TemperatureHumiditySensor:
    def read(self) -> EnvironmentReading:
        return EnvironmentReading(temperature_c=24.0, humidity_percent=61.0)


class GPSSensor:
    def read(self) -> GPSReading:
        return GPSReading(latitude=36.8529, longitude=-75.9780, accuracy_m=2.5)


class PlotMapper:
    def __init__(self, width_m: float, length_m: float):
        self.width_m = width_m
        self.length_m = length_m

    def map_plot(self, gps: GPSReading) -> Plot:
        print("[MAPPER] Origin established at local coordinate (0, 0).")
        print("[MAPPER] Simulating perimeter scan...")
        boundary = [
            (0.0, 0.0),
            (self.width_m, 0.0),
            (self.width_m, self.length_m),
            (0.0, self.length_m),
        ]
        for point in boundary:
            print(f"         boundary -> ({point[0]:.1f}m, {point[1]:.1f}m)")
            time.sleep(0.2)
        return Plot(
            width_m=self.width_m,
            length_m=self.length_m,
            origin_latitude=gps.latitude,
            origin_longitude=gps.longitude,
            boundary_points=boundary,
        )


class Planter:
    def __init__(self):
        self.seed_inventory: dict[str, int] = {}

    @property
    def seed_count(self) -> int:
        return sum(self.seed_inventory.values())

    def load_seeds(self, counts: dict[str, int]) -> None:
        self.seed_inventory = dict(counts)

    def has_seed(self, plant: str) -> bool:
        return self.seed_inventory.get(plant, 0) > 0

    def plant(self, cell: PlantingCell) -> bool:
        if not self.has_seed(cell.plant):
            return False

        print(
            f"[PLANTER] Planting {cell.plant} at "
            f"({cell.x_m:.2f}m, {cell.y_m:.2f}m), "
            f"depth={cell.planting_depth_m:.3f}m"
        )
        time.sleep(0.15)
        self.seed_inventory[cell.plant] -= 1
        return True


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

class PlantRecommendationEngine:
    def recommend(
        self,
        environment: EnvironmentReading,
        gps: GPSReading,
        now: datetime,
    ) -> list[PlantRecommendation]:
        recommendations = []
        for plant in PLANT_CATALOG:
            temp_ok = plant.min_temp_c <= environment.temperature_c <= plant.max_temp_c
            humidity_ok = environment.humidity_percent <= plant.max_humidity_percent
            month_ok = now.month in plant.preferred_months
            if temp_ok and humidity_ok and month_ok:
                recommendations.append(
                    PlantRecommendation(
                        name=plant.name,
                        reason=(
                            f"{environment.temperature_c:.1f}°C, "
                            f"{environment.humidity_percent:.0f}% humidity, "
                            f"month={now.month}, "
                            f"GPS={gps.latitude:.4f},{gps.longitude:.4f}"
                        ),
                        spacing_m=plant.spacing_m,
                        planting_depth_m=plant.planting_depth_m,
                    )
                )

        if not recommendations:
            fallback = CATALOG_BY_NAME["Bush Bean"]
            recommendations.append(
                PlantRecommendation(
                    name=fallback.name,
                    reason="Fallback demo crop; production software should use local agronomy data.",
                    spacing_m=fallback.spacing_m,
                    planting_depth_m=fallback.planting_depth_m,
                )
            )
        return recommendations


# ---------------------------------------------------------------------------
# Quantity-driven grid planner
# ---------------------------------------------------------------------------

class GridPlanner:
    EDGE_MARGIN_M = 0.25

    def create_grid(
        self,
        plot: Plot,
        seed_plan: dict[str, int],
    ) -> list[PlantingCell]:
        if not seed_plan:
            raise ValueError("The planting plan contains no seeds.")

        usable_width = plot.width_m - 2 * self.EDGE_MARGIN_M
        if usable_width <= 0:
            raise ValueError("Plot is too narrow for the configured edge margin.")

        # Each plant type gets a horizontal band. Within that band, the number
        # of columns is determined by spacing and the seed count; only exactly
        # the requested number of slots are created.
        band_specs = []
        for plant_name, count in seed_plan.items():
            if count <= 0:
                continue
            plant = CATALOG_BY_NAME[plant_name]
            columns = max(1, int(math.floor(usable_width / plant.spacing_m)) + 1)
            columns = min(columns, count)
            rows = math.ceil(count / columns)
            required_height = (rows - 1) * plant.spacing_m + 2 * self.EDGE_MARGIN_M
            band_specs.append((plant_name, count, columns, rows, required_height))

        total_required_length = sum(spec[4] for spec in band_specs)
        if total_required_length > plot.length_m + 1e-9:
            raise ValueError(
                f"The requested seed counts require about {total_required_length:.2f}m "
                f"of plot length, but the mapped plot is {plot.length_m:.2f}m long. "
                "Reduce seed counts or map a larger plot."
            )

        # Center the complete set of bands vertically in the mapped plot.
        y_cursor = max(self.EDGE_MARGIN_M, (plot.length_m - total_required_length) / 2)
        cells: list[PlantingCell] = []
        global_row = 0

        for plant_name, count, columns, rows, band_height in band_specs:
            plant = CATALOG_BY_NAME[plant_name]
            band_y_start = y_cursor + self.EDGE_MARGIN_M
            placed = 0

            for row in range(rows):
                y = band_y_start + row * plant.spacing_m
                for column in range(columns):
                    if placed >= count:
                        break
                    x = self.EDGE_MARGIN_M + column * plant.spacing_m
                    cells.append(
                        PlantingCell(
                            row=global_row,
                            column=column,
                            x_m=round(x, 3),
                            y_m=round(y, 3),
                            plant=plant_name,
                            spacing_m=plant.spacing_m,
                            planting_depth_m=plant.planting_depth_m,
                        )
                    )
                    placed += 1
                global_row += 1

            y_cursor += band_height

        return cells


# ---------------------------------------------------------------------------
# Local app
# ---------------------------------------------------------------------------

class AppServer:
    def __init__(self, robot: "FarmingRobot"):
        self.robot = robot
        self.server = HTTPServer((APP_HOST, APP_PORT), self._handler_class())

    def _handler_class(self):
        robot = self.robot

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, payload: dict, status: int = 200):
                body = json.dumps(payload, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self) -> dict:
                length = int(self.headers.get("Content-Length", "0"))
                if length == 0:
                    return {}
                raw = self.rfile.read(length).decode("utf-8")
                return json.loads(raw)

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/api/state":
                    self._send_json(robot.api_state())
                    return
                if path == "/":
                    self._send_html(robot.render_app())
                    return
                if path.startswith("/thumbs/"):
                    self._send_thumbnail(path)
                    return
                self._send_json({"error": "not found"}, 404)

            def _send_thumbnail(self, path: str):
                requested_name = unquote(path[len("/thumbs/"):])
                if not requested_name or "/" in requested_name or "\\" in requested_name:
                    self._send_json({"error": "invalid thumbnail path"}, 400)
                    return

                thumbnail_path = os.path.realpath(os.path.join(THUMBS_DIR, requested_name))
                thumbs_root = os.path.realpath(THUMBS_DIR)
                if not thumbnail_path.startswith(thumbs_root + os.sep):
                    self._send_json({"error": "invalid thumbnail path"}, 400)
                    return
                if not os.path.isfile(thumbnail_path):
                    self._send_json({"error": "thumbnail not found"}, 404)
                    return

                try:
                    with open(thumbnail_path, "rb") as image_file:
                        body = image_file.read()
                except OSError:
                    self._send_json({"error": "unable to read thumbnail"}, 500)
                    return

                content_type = mimetypes.guess_type(thumbnail_path)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=3600")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self, html: str):
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                path = urlparse(self.path).path
                try:
                    data = self._read_json()
                    if path == "/api/add-plant":
                        result = robot.add_plant_to_plan(data.get("plant"), data.get("count", 1))
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    if path == "/api/remove-plant":
                        result = robot.remove_one_plant_from_plan(data.get("plant"))
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    if path == "/api/confirm":
                        result = robot.confirm_plan()
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    if path == "/api/load-seeds":
                        result = robot.load_seeds(data.get("counts", {}))
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    self._send_json({"error": "not found"}, 404)
                except Exception as exc:
                    self._send_json({"ok": False, "error": str(exc)}, 400)

            def log_message(self, format, *args):
                return

        return Handler

    def start(self):
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        print(f"[APP] Local control app running at http://{APP_HOST}:{APP_PORT}")

    def stop(self):
        self.server.shutdown()


# ---------------------------------------------------------------------------
# Main robot
# ---------------------------------------------------------------------------

class FarmingRobot:
    def __init__(self):
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

        self.confirmed = False
        self.current_cell_index = 0
        self.message = "Waiting for start button."
        self.app_server = AppServer(self)

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
            print("\n[ROBOT] Planting sequence complete. Plant profiles created.")
        except KeyboardInterrupt:
            self.state = RobotState.ERROR
            self.message = "Stopped by user."
            print("\n[ROBOT] Stopped.")
        except Exception as exc:
            self.state = RobotState.ERROR
            self.message = f"Error: {exc}"
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

    def plant_all(self):
        self.state = RobotState.PLANTING
        self.current_cell_index = 0
        total = len(self.planting_cells)

        for index, cell in enumerate(self.planting_cells, start=1):
            self.current_cell_index = index - 1
            self.message = f"Planting {index}/{total}: {cell.plant}"
            if not self.planter.plant(cell):
                raise RuntimeError(f"Planter ran out of {cell.plant} seeds.")
            cell.status = "planted"
            self.create_profile_for_cell(cell)
            print(f"[ROBOT] Progress: {index}/{total}")

    def add_profile_img(self, plant):
        for img in os.listdir("./thumbs"):
            # Remove the file extension
            img_name = re.sub(r"\.svg$", "", img, flags=re.IGNORECASE)

            # Normalize spaces/underscores/hyphens
            img_name = re.sub(r"[\s_-]+", " ", img_name).strip().lower()

            # Normalize the plant name the same way
            plant_name = re.sub(r"[\s_-]+", " ", plant).strip().lower()

            print(img_name, " ", plant_name)

            if img_name == plant_name:
                return img

        return None
            

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
        }

    def render_app(self) -> str:
        catalog_options = "".join(
            f'<option value="{plant.name}">{plant.name}</option>'
            for plant in PLANT_CATALOG
        )
        return f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpaceFruit Farming Robot</title>
<style>
:root {{ font-family: system-ui, sans-serif; color-scheme: light; }}
body {{ max-width: 1200px; margin: 0 auto; padding: 24px; background:#f5f7f2; color:#182018; }}
.card {{ background:white; border:1px solid #d7ddd2; border-radius:14px; padding:20px; margin:16px 0; box-shadow:0 2px 8px #0000000a; }}
h1 {{ margin-top:0; }}
button, select, input {{ padding:9px 11px; border-radius:8px; border:1px solid #aab4a5; font-size:15px; }}
button {{ cursor:pointer; background:#e8f2df; }}
button.primary {{ background:#315c2b; color:white; border-color:#315c2b; }}
button.danger {{ background:#fff0f0; }}
.row {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
.plan-row {{ display:grid; grid-template-columns:1fr 110px 45px; gap:10px; align-items:center; padding:8px 0; border-bottom:1px solid #eee; }}
.badge {{ display:inline-block; padding:5px 9px; border-radius:999px; background:#e8f2df; }}
#error {{ color:#a21c1c; min-height:1.3em; }}
#grid {{ position:relative; width:100%; max-width:900px; aspect-ratio: 6 / 8; background:#edf4e7; border:3px solid #687b5f; overflow:hidden; border-radius:10px; }}
.slot {{ position:absolute; width:44px; height:44px; transform:translate(-50%,-50%); border-radius:50%; border:2px solid #335b2d; background:#cde4bd; cursor:pointer; box-sizing:border-box; font-size:0; display:flex; align-items:center; justify-content:center; padding:4px; overflow:hidden; }}
.slot.planted {{ background:#ffffff; }}
.slot img {{ width:100%; height:100%; object-fit:contain; display:block; pointer-events:none; }}
.slot.selected {{ outline:3px solid #d29b22; }}
#profile {{ min-height:120px; }}
small {{ color:#5f6b5b; }}
table {{ border-collapse:collapse; width:100%; }}
th,td {{ padding:8px; border-bottom:1px solid #e5e8e2; text-align:left; }}
</style>
</head>
<body>
<h1>🌱 SpaceFruit Farming Robot</h1>
<div class="card"><strong>Robot:</strong> <span id="state" class="badge">loading</span><p id="message"></p></div>

<div class="card">
<h2>1. Edit planting plan</h2>
<p>Each quantity is an exact number of seeds/planting slots. Remove one seed at a time or add any plant from the 40-plant catalog.</p>
<div class="row">
<select id="plantSelect">{catalog_options}</select>
<input id="addCount" type="number" min="1" max="1000" value="1" style="width:90px">
<button onclick="addPlant()">Add seeds</button>
</div>
<div id="plan"></div>
<p><strong>Total seeds:</strong> <span id="totalSeeds">0</span></p>
<button class="primary" onclick="confirmPlan()">Confirm planting plan</button>
<div id="error"></div>
</div>

<div class="card">
<h2>2. Load exact seeds</h2>
<p>The robot will not start planting until the loaded quantity matches the plan for every plant type.</p>
<div id="seedInputs"></div>
<button class="primary" onclick="loadSeeds()">Verify loaded seeds</button>
</div>

<div class="card">
<h2>3. Plot / planting grid</h2>
<p>Every circle is one physical planting slot. Click a slot after planting to view its plant profile.</p>
<div id="grid"></div>
<small>Grid coordinates are relative to the robot's startup position (0,0). Band spacing follows the selected plant type's spacing.</small>
</div>

<div class="card">
<h2>4. Plant profile</h2>
<div id="profile">Click a planted slot.</div>
</div>

<div class="card">
<h2>Plant profiles</h2>
<div id="profiles"></div>
</div>

<script>
let latestState = null;

async function api(path, method='GET', body=null) {{
    const options = {{method, headers: {{'Content-Type':'application/json'}}}};
    if (body !== null) options.body = JSON.stringify(body);
    const response = await fetch(path, options);
    return await response.json();
}}

function esc(value) {{
    return String(value ?? '').replace(/[&<>'"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}}[c]));
}}

async function refresh() {{
    latestState = await api('/api/state');
    document.getElementById('state').textContent = latestState.state;
    document.getElementById('message').textContent = latestState.message;
    document.getElementById('totalSeeds').textContent = latestState.total_requested_seeds;
    renderPlan();
    renderSeedInputs();
    renderGrid();
    renderProfiles();
}}

function renderPlan() {{
    const entries = Object.entries(latestState.seed_plan || {{}});
    const el = document.getElementById('plan');
    if (!entries.length) {{ el.innerHTML = '<p>No seeds selected yet.</p>'; return; }}
    el.innerHTML = entries.map(([plant, count]) => `
      <div class="plan-row">
        <strong>${{esc(plant)}}</strong>
        <span>${{count}} seed${{count === 1 ? '' : 's'}}</span>
        <button class="danger" onclick="removePlant('${{encodeURIComponent(plant)}}')">−1</button>
      </div>`).join('');
}}

function renderSeedInputs() {{
    const entries = Object.entries(latestState.seed_plan || {{}});
    const el = document.getElementById('seedInputs');
    if (!entries.length) {{ el.innerHTML = '<p>Confirm a plan first.</p>'; return; }}
    el.innerHTML = entries.map(([plant, count]) => `
      <div class="row" style="margin:8px 0">
        <strong style="width:180px">${{esc(plant)}}</strong>
        <span>Need ${{count}}</span>
        <input id="seed-${{encodeURIComponent(plant)}}" type="number" min="0" value="${{count}}" style="width:100px">
      </div>`).join('');
}}

async function addPlant() {{
    clearError();
    const plant = document.getElementById('plantSelect').value;
    const count = Number(document.getElementById('addCount').value);
    const result = await api('/api/add-plant', 'POST', {{plant, count}});
    if (!result.ok) showError(result.error); else await refresh();
}}

async function removePlant(encodedPlant) {{
    clearError();
    const plant = decodeURIComponent(encodedPlant);
    const result = await api('/api/remove-plant', 'POST', {{plant}});
    if (!result.ok) showError(result.error); else await refresh();
}}

async function confirmPlan() {{
    clearError();
    const result = await api('/api/confirm', 'POST');
    if (!result.ok) {{ showError(result.error); return; }}
    await refresh();
}}

async function loadSeeds() {{
    clearError();
    const counts = {{}};
    for (const [plant, count] of Object.entries(latestState.seed_plan || {{}})) {{
        counts[plant] = Number(document.getElementById('seed-' + encodeURIComponent(plant)).value);
    }}
    const result = await api('/api/load-seeds', 'POST', {{counts}});
    if (!result.ok) showError(result.error); else await refresh();
}}

function renderGrid() {{
    const grid = document.getElementById('grid');
    const cells = latestState.planting_cells || [];
    const plot = latestState.plot;
    if (!plot || !cells.length) {{ grid.innerHTML = '<p style="padding:20px">The quantity-driven grid will appear after plan confirmation.</p>'; return; }}

    grid.innerHTML = cells.map((cell, index) => {{
        const left = (cell.x_m / plot.width_m) * 100;
        const top = (cell.y_m / plot.length_m) * 100;
        const profile = (latestState.plant_profiles || []).find(p => p.profile_id === cell.profile_id);
        const title = profile ? `${{profile.plant_type}} — ${{profile.profile_id}}` : `${{cell.plant}} — pending`;
        const thumbnail = profile && profile.img
            ? `<img src="/thumbs/${{encodeURIComponent(profile.img)}}" alt="${{esc(profile.plant_type)}}" loading="eager">`
            : '';

        return `<button class="slot ${{cell.status === 'planted' ? 'planted' : ''}}" title="${{esc(title)}}" style="left:${{left}}%;top:${{top}}%" onclick="showProfile('${{cell.profile_id || ''}}')">${{thumbnail}}</button>`;
    }}).join('');
}}

function showProfile(id) {{
    const profile = (latestState.plant_profiles || []).find(p => p.profile_id === id);
    if (!profile) {{ document.getElementById('profile').innerHTML = '<p>This slot has not been planted yet.</p>'; return; }}
    document.getElementById('profile').innerHTML = `
      <h3>${{esc(profile.plant_type)}} <small>(${{esc(profile.profile_id)}})</small></h3>
      <table>
      <tr><th>Img</th><td>${{profile.img}}</td></tr>
      <tr><th>Age</th><td>${{profile.age_days}} days</td></tr>
      <tr><th>Planted</th><td>${{esc(profile.planted_at)}}</td></tr>
      <tr><th>Location</th><td>(${{profile.x_m}}m, ${{profile.y_m}}m)</td></tr>
      <tr><th>Spacing</th><td>${{profile.spacing_m}}m</td></tr>
      <tr><th>Planting depth</th><td>${{profile.planting_depth_m}}m</td></tr>
      <tr><th>Sunlight</th><td>${{esc(profile.sunlight)}}</td></tr>
      <tr><th>Water needs</th><td>${{esc(profile.water_needs)}}</td></tr>
      <tr><th>Typical germination</th><td>${{profile.typical_germination_days}} days</td></tr>
      <tr><th>Conditions at planting</th><td>${{profile.temperature_at_planting_c}}°C / ${{profile.humidity_at_planting_percent}}% RH</td></tr>
      <tr><th>Health</th><td>${{esc(profile.health_status)}}</td></tr>
      </table>`;
}}

function renderProfiles() {{
    const profiles = latestState.plant_profiles || [];
    const el = document.getElementById('profiles');
    if (!profiles.length) {{ el.innerHTML = '<p>No plant profiles yet. Profiles are created as each seed is planted.</p>'; return; }}
    el.innerHTML = `<table><tr><th>ID</th><th>Type</th><th>Age</th><th>Location</th><th>Status</th></tr>` +
      profiles.map(p => `<tr><td>${{esc(p.profile_id)}}</td><td>${{esc(p.plant_type)}}</td><td>${{p.age_days}} days</td><td>(${{p.x_m}}, ${{p.y_m}})</td><td>${{esc(p.health_status)}}</td></tr>`).join('') + '</table>';
}}

function showError(message) {{ document.getElementById('error').textContent = message; }}
function clearError() {{ document.getElementById('error').textContent = ''; }}

setInterval(refresh, 1000);
refresh();
</script>
</body>
</html>'''


def main():
    robot = FarmingRobot()
    robot.run()


if __name__ == "__main__":
    main()
