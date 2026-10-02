import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from spacefruit.vision import DiseaseDetection


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


    def test_state_revision_increases_once_per_completed_seed(self):
        self.prepare_plan(3)
        with patch.object(main.time, "sleep", return_value=None):
            self.robot.plant_all()

        self.assertEqual(self.robot.state_revision, 3)
        self.assertEqual(self.robot.planted_counts["Tomato"], 3)
        state = self.robot.api_state()
        self.assertEqual(state["state_revision"], 3)
        self.assertEqual(sum(1 for cell in state["planting_cells"] if cell["status"] == "planted"), 3)

    def test_extra_seed_of_same_type_gets_its_own_profile(self):
        self.prepare_plan(6)
        with patch.object(main.time, "sleep", return_value=None):
            self.robot.plant_all()

        tomato_cells = [c for c in self.robot.planting_cells if c.plant == "Tomato"]
        tomato_profiles = [p for p in self.robot.plant_profiles.values() if p.plant_type == "Tomato"]
        self.assertEqual(len(tomato_cells), 6)
        self.assertEqual(len(tomato_profiles), 6)
        self.assertTrue(all(c.status == "planted" and c.profile_id for c in tomato_cells))

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

            import spacefruit.robot as robot_module
            original = robot_module.THUMBS_DIR
            try:
                robot_module.THUMBS_DIR = str(root)
                self.assertEqual(self.robot.add_profile_img("Test Plant"), "png/Test Plant.png")
            finally:
                robot_module.THUMBS_DIR = original


    def test_start_inspection_visits_every_planted_profile(self):
        self.prepare_plan(3)
        with patch.object(main.time, "sleep", return_value=None):
            self.robot.plant_all()

        self.robot.state = main.RobotState.COMPLETE
        result = self.robot.start_inspection()
        self.assertTrue(result["ok"], result)

        self.robot.inspection_thread.join(timeout=2)

        self.assertEqual(self.robot.state, main.RobotState.INSPECTION_COMPLETE)
        self.assertEqual(len(self.robot.inspection_results), 3)
        self.assertEqual(len(self.robot.health_alerts), 0)
        self.assertTrue(all(
            profile.last_inspected_at and profile.last_inspection_id
            for profile in self.robot.plant_profiles.values()
        ))

    def test_inspection_surfaces_model_health_alert(self):
        self.prepare_plan(1)
        with patch.object(main.time, "sleep", return_value=None):
            self.robot.plant_all()

        class FakeDiseaseModel:
            def analyze(self, frame, plant_type):
                return DiseaseDetection(
                    detected=True,
                    condition="leaf spot",
                    confidence=0.91,
                    notes="test detection",
                )

        self.robot.health_model = FakeDiseaseModel()
        self.robot.health_inspector.health_model = self.robot.health_model
        self.robot.state = main.RobotState.COMPLETE

        result = self.robot.start_inspection()
        self.assertTrue(result["ok"], result)
        self.robot.inspection_thread.join(timeout=2)

        self.assertEqual(len(self.robot.health_alerts), 1)
        self.assertEqual(self.robot.health_alerts[0]["condition"], "leaf spot")
        profile = next(iter(self.robot.plant_profiles.values()))
        self.assertIn("leaf spot", profile.health_status)


if __name__ == "__main__":
    unittest.main()
