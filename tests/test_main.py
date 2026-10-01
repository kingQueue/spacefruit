import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class SpaceFruitPlantingTests(unittest.TestCase):
    def setUp(self):
        self.robot = main.FarmingRobot(start_server=False)
        self.robot.environment = main.EnvironmentReading(24.0, 61.0)
        self.robot.plot = main.Plot(
            width_m=6.0,
            length_m=8.0,
            origin_latitude=0.0,
            origin_longitude=0.0,
            boundary_points=[],
        )

    def prepare_plan(self, count=2):
        self.robot.seed_plan = {"Tomato": count}
        self.robot.state = main.RobotState.WAITING_FOR_SEEDS
        self.robot.create_planting_plan()
        result = self.robot.load_seeds({"Tomato": count})
        self.assertTrue(result["ok"], result)

    def test_grid_contains_exact_number_of_seeds(self):
        self.robot.seed_plan = {"Tomato": 2, "Basil": 3}
        self.robot.state = main.RobotState.WAITING_FOR_SEEDS
        self.robot.create_planting_plan()
        self.assertEqual(len(self.robot.planting_cells), 5)

    def test_successful_planting_creates_one_profile_per_seed(self):
        self.prepare_plan(2)
        with patch.object(main.time, "sleep", return_value=None):
            self.robot.plant_all()

        self.assertEqual(len(self.robot.plant_profiles), 2)
        self.assertEqual(self.robot.planted_counts["Tomato"], 2)
        self.assertEqual(self.robot.planter.seed_count, 0)
        self.assertTrue(all(cell.status == "planted" for cell in self.robot.planting_cells))
        self.assertTrue(all(cell.profile_id in self.robot.plant_profiles for cell in self.robot.planting_cells))
        self.assertTrue(all(profile.img for profile in self.robot.plant_profiles.values()))

    def test_grid_count_mismatch_has_specific_error(self):
        self.robot.seed_plan = {"Tomato": 2}
        self.robot.state = main.RobotState.WAITING_FOR_SEEDS
        self.robot.planting_cells = self.robot.grid_planner.create_grid(self.robot.plot, {"Tomato": 1})
        self.robot.planter.load_seeds({"Tomato": 2})

        with self.assertRaises(main.PlantingStepError) as ctx:
            self.robot.plant_all()

        self.assertEqual(ctx.exception.code, "GRID_COUNT_MISMATCH")

    def test_failed_seed_dispense_has_specific_error_and_stays_unconfirmed(self):
        self.prepare_plan(1)
        self.robot.planter.plant = lambda cell: False

        with self.assertRaises(main.PlantingStepError) as ctx:
            self.robot.plant_all()

        self.assertEqual(ctx.exception.code, "SEED_DISPENSE_FAILED")
        self.assertEqual(self.robot.planting_cells[0].status, "pending")
        self.assertEqual(len(self.robot.plant_profiles), 0)
        self.assertTrue(self.robot.planting_cells[0].error)

    def test_thumbnail_resolver_finds_nested_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "png").mkdir()
            (root / "png" / "Test Plant.png").write_bytes(b"png")
            (root / "default.svg").write_text("<svg/>", encoding="utf-8")

            original = main.THUMBS_DIR
            try:
                main.THUMBS_DIR = str(root)
                self.assertEqual(self.robot.add_profile_img("Test Plant"), "png/Test Plant.png")
            finally:
                main.THUMBS_DIR = original


if __name__ == "__main__":
    unittest.main()
