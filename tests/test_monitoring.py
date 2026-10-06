import unittest
from unittest.mock import patch

import main
from spacefruit.models import EnvironmentReading, Plot
from spacefruit.monitoring import (
    CameraFrame,
    HealthAnalysis,
    MonitoringWorkflow,
    SimulatedCamera,
    SimulatedHealthModel,
    SimulatedWeedModel,
    WeedAnalysis,
)


class FixedRandom:
    """Small deterministic stand-in for random.Random in simulation tests."""

    def __init__(self, random_value=0.1):
        self.random_value = random_value

    def randint(self, low, high):
        return high

    def sample(self, values, count):
        return list(values)[:count]

    def choice(self, values):
        return values[0]

    def random(self):
        return self.random_value


def make_robot(plant_count=3):
    robot = main.FarmingRobot(start_server=False)
    robot.environment = EnvironmentReading(24.0, 61.0)
    robot.plot = Plot(6.0, 8.0, 0.0, 0.0, [])
    robot.seed_plan = {"Tomato": plant_count}
    robot.state = main.RobotState.WAITING_FOR_SEEDS
    robot.create_planting_plan()
    loaded = robot.load_seeds({"Tomato": plant_count})
    assert loaded["ok"], loaded
    with patch("spacefruit.hardware.time.sleep", return_value=None):
        robot.plant_all()
    robot.state = main.RobotState.COMPLETE
    return robot


class SimulatedCameraTests(unittest.TestCase):
    def test_camera_captures_a_frame_for_the_current_plant(self):
        robot = make_robot(1)
        cell = robot.planting_cells[0]

        frame = SimulatedCamera().capture(cell)

        self.assertTrue(frame.captured)
        self.assertEqual(frame.cell_id, cell.profile_id)
        self.assertTrue(frame.image_path.startswith("simulated://camera/"))

    def test_camera_health_model_flags_one_or_two_plants_with_camera_issues(self):
        robot = make_robot(4)
        profiles = list(robot.plant_profiles.values())
        model = SimulatedHealthModel(rng=FixedRandom())
        model.prepare_scan(profiles)

        results = [
            model.analyze(CameraFrame(p.profile_id, captured=True), p)
            for p in profiles
        ]

        affected = [result for result in results if result.issue_detected]
        self.assertEqual(len(affected), 2)
        self.assertEqual(affected[0].issues, ["possible malnutrition"])
        self.assertIn("Camera detected", affected[0].summary)
        self.assertTrue(all(not result.issues for result in results if not result.issue_detected))

    def test_health_model_does_not_report_issues_without_a_captured_frame(self):
        robot = make_robot(1)
        profile = next(iter(robot.plant_profiles.values()))
        model = SimulatedHealthModel(rng=FixedRandom())
        model.prepare_scan([profile])

        result = model.analyze(CameraFrame(profile.profile_id, captured=False), profile)

        self.assertFalse(result.issue_detected)
        self.assertEqual(result.issues, [])

    def test_camera_weed_model_detects_and_counts_weeds(self):
        robot = make_robot(1)
        cell = robot.planting_cells[0]
        model = SimulatedWeedModel(rng=FixedRandom(), detection_rate=0.5)

        result = model.analyze(CameraFrame(cell.profile_id, captured=True), cell)

        self.assertTrue(result.weed_detected)
        self.assertEqual(result.weeds_found, 2)
        self.assertIn("Camera detected", result.summary)

    def test_camera_weed_model_ignores_uncaptured_frames(self):
        robot = make_robot(1)
        cell = robot.planting_cells[0]
        model = SimulatedWeedModel(rng=FixedRandom(), detection_rate=1.0)

        result = model.analyze(CameraFrame(cell.profile_id, captured=False), cell)

        self.assertFalse(result.weed_detected)
        self.assertEqual(result.weeds_found, 0)


class MonitoringFlowTests(unittest.TestCase):
    def test_each_location_is_weeded_before_health_check_and_alerts_are_recorded(self):
        robot = make_robot(3)
        events = []

        class Camera:
            def capture(self, cell):
                events.append(("camera", cell.profile_id))
                return CameraFrame(cell.profile_id, captured=True)

        class WeedModel:
            def analyze(self, frame, cell):
                events.append(("weed_scan", cell.profile_id))
                return WeedAnalysis(True, 1, "Camera detected one weed.")

        class HealthModel:
            def analyze(self, frame, profile):
                events.append(("health_scan", profile.profile_id))
                if profile == list(robot.plant_profiles.values())[0]:
                    return HealthAnalysis(True, ["possible root rot"], "Possible root rot")
                return HealthAnalysis(False, [], "Camera scan clear")

        def pluck(count, cell):
            events.append(("pluck", cell.profile_id))
            return count

        robot.weed_remover.pluck = pluck
        workflow = MonitoringWorkflow(
            robot,
            camera=Camera(),
            weed_model=WeedModel(),
            health_model=HealthModel(),
        )

        with patch("spacefruit.monitoring.time.sleep", return_value=None):
            workflow.run()

        self.assertEqual(len(events), 12)
        for offset in range(0, len(events), 4):
            self.assertEqual([event[0] for event in events[offset:offset + 4]], [
                "camera", "weed_scan", "pluck", "health_scan",
            ])
            self.assertEqual(len({event[1] for event in events[offset:offset + 4]}), 1)

        monitoring = robot.monitoring
        self.assertEqual(monitoring["completed"], 3)
        self.assertEqual(monitoring["weeding_completed"], 3)
        self.assertEqual(monitoring["weeding_total"], 3)
        self.assertEqual(monitoring["weeding_percent"], 100)
        self.assertEqual(monitoring["weeds_removed"], 3)
        self.assertEqual(monitoring["issues_detected"], 1)
        self.assertEqual(monitoring["alerts"][0]["issues"], ["possible root rot"])
        self.assertIn("Camera alert", monitoring["alerts"][0]["message"])
        self.assertTrue(all(cell.weeding_completed for cell in robot.planting_cells))
        self.assertTrue(all(cell.weeds_removed == 1 for cell in robot.planting_cells))
        self.assertEqual(robot.state, main.RobotState.COMPLETE)
        self.assertFalse(monitoring["running"])

    def test_default_monitoring_model_creates_one_or_two_alerts(self):
        robot = make_robot(4)
        workflow = MonitoringWorkflow(robot, health_model=SimulatedHealthModel(rng=FixedRandom()))

        with patch("spacefruit.monitoring.time.sleep", return_value=None):
            workflow.run()

        self.assertIn(robot.monitoring["issues_detected"], (1, 2))
        self.assertEqual(len(robot.monitoring["alerts"]), robot.monitoring["issues_detected"])
        self.assertTrue(all("malnutrition" in alert["issues"][0] for alert in robot.monitoring["alerts"]))


if __name__ == "__main__":
    unittest.main()
