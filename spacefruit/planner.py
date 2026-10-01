"""Quantity-driven planting grid planner."""

from __future__ import annotations

import math

from .catalog import CATALOG_BY_NAME
from .models import Plot, PlantingCell

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


