"""Hardware and sensor simulation components."""

from __future__ import annotations

import time

from .models import EnvironmentReading, GPSReading, Plot, PlantingCell

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




class WeedRemover:
    """Hardware abstraction for physically plucking a detected weed."""

    def pluck(self, weed_count: int, cell) -> int:
        if weed_count <= 0:
            return 0
        # Simulation: report that every model-detected weed was removed.
        return weed_count
