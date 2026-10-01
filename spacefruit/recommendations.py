"""Plant recommendation engine."""

from __future__ import annotations

from datetime import datetime

from .catalog import CATALOG_BY_NAME, PLANT_CATALOG
from .models import EnvironmentReading, GPSReading, PlantRecommendation

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


