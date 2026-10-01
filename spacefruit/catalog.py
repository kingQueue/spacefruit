"""Plant catalog and lookup data."""

from .models import PlantCatalogEntry

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


