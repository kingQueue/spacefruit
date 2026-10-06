import unittest
from unittest.mock import patch

import main
from spacefruit.harvesting import HarvestAnalysis, SimulatedHarvestReadinessModel
from spacefruit.models import EnvironmentReading, Plot, RobotState
from spacefruit.monitoring import CameraFrame


class FixedRandom:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


class FixedReadinessModel:
    def __init__(self, ready, events=None):
        self.ready = ready
        self.events = events if events is not None else []

    def analyze(self, frame, profile):
        self.events.append(("camera_check", frame.cell_id, profile.profile_id))
        return HarvestAnalysis(self.ready, "Camera confirms ripe." if self.ready else "Not ripe yet.")


def make_robot(plant_count=1):
    robot = main.FarmingRobot(start_server=False)
    robot.environment = EnvironmentReading(24.0, 61.0)
    robot.plot = Plot(6.0, 8.0, 0.0, 0.0, [])
    robot.seed_plan = {"Tomato": plant_count}
    robot.state = RobotState.WAITING_FOR_SEEDS
    robot.create_planting_plan()
    result = robot.load_seeds({"Tomato": plant_count})
    assert result["ok"], result
    with patch("spacefruit.hardware.time.sleep", return_value=None):
        robot.plant_all()
    robot.state = RobotState.COMPLETE
    return robot


class HarvestFlowTests(unittest.TestCase):
    def test_camera_readiness_simulation_supports_ready_and_not_ready(self):
        robot = make_robot()
        profile = next(iter(robot.plant_profiles.values()))
        ready_model = SimulatedHarvestReadinessModel(rng=FixedRandom(0.1), readiness_rate=0.5)
        not_ready_model = SimulatedHarvestReadinessModel(rng=FixedRandom(0.9), readiness_rate=0.5)

        ready = ready_model.analyze(CameraFrame(profile.profile_id, captured=True), profile)
        not_ready = not_ready_model.analyze(CameraFrame(profile.profile_id, captured=True), profile)

        self.assertTrue(ready.ready)
        self.assertIn("ready to harvest", ready.summary)
        self.assertFalse(not_ready.ready)
        self.assertIn("not ready", not_ready.summary)

    def test_camera_refuses_to_mark_an_uncaptured_plant_ready(self):
        robot = make_robot()
        profile = next(iter(robot.plant_profiles.values()))
        model = SimulatedHarvestReadinessModel(rng=FixedRandom(0.0), readiness_rate=1.0)

        result = model.analyze(CameraFrame(profile.profile_id, captured=False), profile)

        self.assertFalse(result.ready)
        self.assertIn("could not capture", result.summary)

    def test_ready_plant_is_harvested_into_inventory_after_camera_check(self):
        robot = make_robot()
        profile = next(iter(robot.plant_profiles.values()))
        cell = robot.planting_cells[0]
        events = []

        class Camera:
            def capture(self, current_cell):
                events.append(("capture", current_cell.profile_id))
                return CameraFrame(current_cell.profile_id, captured=True)

        robot.harvest_camera = Camera()
        robot.harvest_readiness_model = FixedReadinessModel(True, events)

        def harvest(current_profile, current_cell):
            events.append(("harvest", current_cell.profile_id))
            return True

        robot.harvester.harvest = harvest
        result = robot.start_harvest(profile.profile_id)
        self.assertTrue(result["ok"], result)
        robot.harvest_thread.join(timeout=2)

        self.assertFalse(robot.harvest_thread.is_alive())
        self.assertEqual([event[0] for event in events], ["capture", "camera_check", "harvest"])
        self.assertEqual(events[0][1], events[1][1])
        self.assertEqual(events[1][1], events[2][1])
        self.assertTrue(profile.harvest_ready)
        self.assertEqual(profile.harvest_status, "harvested")
        self.assertTrue(profile.harvested_at)
        self.assertEqual(cell.status, "empty_plot")
        empty_profile = robot.plant_profiles[cell.profile_id]
        self.assertEqual(empty_profile.plant_type, "Empty Plot")
        self.assertNotIn(profile.profile_id, robot.plant_profiles)
        self.assertEqual((empty_profile.x_m, empty_profile.y_m), (cell.x_m, cell.y_m))
        self.assertEqual(robot.harvest_inventory, {"Tomato": 1})
        inventory_item = robot.api_state()["harvest_inventory_items"][0]
        self.assertEqual(inventory_item["plant_type"], "Tomato")
        self.assertEqual(inventory_item["quantity"], 1)
        self.assertTrue(inventory_item["img"])
        self.assertEqual(robot.harvested_items[0]["profile_id"], profile.profile_id)
        self.assertEqual(robot.harvested_items[0]["quantity"], 1)
        self.assertEqual(robot.state, RobotState.COMPLETE)
        self.assertEqual(robot.operation.status, "completed")

    def test_inventory_aggregates_quantity_for_same_plant_and_keeps_thumbnail(self):
        robot = make_robot(plant_count=2)
        robot.harvest_readiness_model = FixedReadinessModel(True)
        robot.harvester.harvest = lambda current_profile, current_cell: True
        expected_thumbnail = next(iter(robot.plant_profiles.values())).img

        for profile in list(robot.plant_profiles.values()):
            result = robot.start_harvest(profile.profile_id)
            self.assertTrue(result["ok"], result)
            robot.harvest_thread.join(timeout=2)

        inventory = robot.api_state()["harvest_inventory_items"]
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0]["plant_type"], "Tomato")
        self.assertEqual(inventory[0]["quantity"], 2)
        self.assertEqual(inventory[0]["img"], expected_thumbnail)

    def test_empty_plot_can_be_replanted_with_one_new_plant_profile(self):
        robot = make_robot()
        old_profile = next(iter(robot.plant_profiles.values()))
        robot.harvest_readiness_model = FixedReadinessModel(True)
        robot.harvester.harvest = lambda current_profile, current_cell: True
        robot.start_harvest(old_profile.profile_id)
        robot.harvest_thread.join(timeout=2)
        cell = robot.planting_cells[0]
        empty_id = cell.profile_id
        empty_profile = robot.plant_profiles[empty_id]
        events = []
        original_plant = robot.planter.plant

        def record_single_plant(candidate):
            events.append((candidate.plant, candidate.x_m, candidate.y_m))
            return original_plant(candidate)

        robot.planter.plant = record_single_plant
        with patch("spacefruit.hardware.time.sleep", return_value=None):
            result = robot.start_replant(empty_id, "Cucumber")
            self.assertTrue(result["ok"], result)
            robot.workflow_thread.join(timeout=2)

        self.assertEqual(events, [("Cucumber", cell.x_m, cell.y_m)])
        self.assertEqual(cell.status, "planted")
        self.assertEqual(cell.plant, "Cucumber")
        self.assertNotEqual(cell.profile_id, empty_id)
        self.assertNotIn(empty_id, robot.plant_profiles)
        new_profile = robot.plant_profiles[cell.profile_id]
        self.assertEqual(new_profile.plant_type, "Cucumber")
        self.assertEqual((new_profile.x_m, new_profile.y_m), (empty_profile.x_m, empty_profile.y_m))
        self.assertEqual(robot.planter.seed_count, 0)
        self.assertEqual(robot.state, RobotState.COMPLETE)
        self.assertEqual(robot.operation.status, "completed")

    def test_replant_rejects_non_empty_profiles_and_unknown_plants(self):
        robot = make_robot()
        plant_profile = next(iter(robot.plant_profiles.values()))
        self.assertFalse(robot.start_replant(plant_profile.profile_id, "Cucumber")["ok"])
        robot.harvest_readiness_model = FixedReadinessModel(True)
        robot.harvester.harvest = lambda current_profile, current_cell: True
        robot.start_harvest(plant_profile.profile_id)
        robot.harvest_thread.join(timeout=2)
        empty_profile = next(p for p in robot.plant_profiles.values() if p.plant_type == "Empty Plot")
        self.assertFalse(robot.start_replant(empty_profile.profile_id, "Imaginary Plant")["ok"])
        self.assertEqual(robot.planting_cells[0].status, "empty_plot")

    def test_not_ready_plant_stays_in_the_plot_and_is_not_added_to_inventory(self):
        robot = make_robot()
        profile = next(iter(robot.plant_profiles.values()))
        cell = robot.planting_cells[0]
        robot.harvest_readiness_model = FixedReadinessModel(False)

        result = robot.start_harvest(profile.profile_id)
        self.assertTrue(result["ok"], result)
        robot.harvest_thread.join(timeout=2)

        self.assertFalse(robot.harvest_thread.is_alive())
        self.assertFalse(profile.harvest_ready)
        self.assertEqual(profile.harvest_status, "not_ready")
        self.assertEqual(cell.status, "planted")
        self.assertEqual(robot.harvest_inventory, {})
        self.assertEqual(robot.harvested_items, [])
        self.assertEqual(robot.state, RobotState.COMPLETE)
        self.assertEqual(robot.operation.status, "completed")

    def test_harvest_rejects_unknown_and_already_harvested_profiles(self):
        robot = make_robot()
        profile = next(iter(robot.plant_profiles.values()))
        robot.harvest_readiness_model = FixedReadinessModel(True)
        robot.harvester.harvest = lambda current_profile, current_cell: True

        self.assertFalse(robot.start_harvest("missing-profile")["ok"])
        result = robot.start_harvest(profile.profile_id)
        self.assertTrue(result["ok"], result)
        robot.harvest_thread.join(timeout=2)

        second_attempt = robot.start_harvest(profile.profile_id)
        self.assertFalse(second_attempt["ok"])
        self.assertEqual(robot.harvest_inventory, {"Tomato": 1})


if __name__ == "__main__":
    unittest.main()
