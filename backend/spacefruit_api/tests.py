import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spacefruit_api.settings")

import django
django.setup()

from django.test import Client, SimpleTestCase
from spacefruit.harvesting import HarvestAnalysis
from spacefruit.robot import FarmingRobot
import spacefruit_api.views as views


class SpaceFruitApiTests(SimpleTestCase):
    def setUp(self):
        views.robot = FarmingRobot(start_server=False)
        self.client = Client()

    def post(self, path, payload=None):
        response = self.client.post(
            path,
            data=payload or {},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_state_endpoint_works(self):
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        self.assertIn("operation", response.json())

    def test_complete_button_flow_marks_every_plant_planted(self):
        with patch("spacefruit.hardware.time.sleep", return_value=None):
            self.post("/api/start")
            self.assertEqual(views.robot.state.value, "waiting_for_confirmation")

            self.post("/api/add-plant", {"plant": "Tomato", "count": 2})
            self.post("/api/add-plant", {"plant": "Lettuce", "count": 1})
            self.post("/api/confirm")

            self.assertEqual(views.robot.state.value, "waiting_for_seeds")
            self.post("/api/load-seeds", {"counts": {"Tomato": 2, "Lettuce": 1}})

            self.assertEqual(views.robot.state.value, "waiting_for_seeds")
            result = self.post("/api/start-planting")
            self.assertTrue(result["ok"])

            views.robot.workflow_thread.join(timeout=5)

            state = self.client.get("/api/state").json()
            self.assertFalse(views.robot.workflow_thread.is_alive())
            self.assertEqual(state["state"], "complete")
            self.assertEqual(state["operation"]["name"], "planting")
            self.assertEqual(state["operation"]["status"], "completed")
            self.assertEqual(len(state["planting_cells"]), 3)
            self.assertEqual(
                sum(cell["status"] == "planted" for cell in state["planting_cells"]),
                3,
            )
            self.assertEqual(len(state["plant_profiles"]), 3)
            self.assertTrue(all(cell["profile_id"] for cell in state["planting_cells"]))
            self.assertEqual(state["seed_count"], 0)

    def test_all_action_endpoints_are_connected(self):
        with patch("spacefruit.hardware.time.sleep", return_value=None):
            self.post("/api/start")
            self.assertTrue(self.post("/api/add-plant", {"plant": "Tomato", "count": 1})["ok"])
            self.assertTrue(self.post("/api/remove-plant", {"plant": "Tomato"})["ok"])
            self.assertTrue(self.post("/api/add-plant", {"plant": "Tomato", "count": 1})["ok"])
            self.assertTrue(self.post("/api/confirm")["ok"])
            self.assertTrue(self.post("/api/load-seeds", {"counts": {"Tomato": 1}})["ok"])
            self.assertTrue(self.post("/api/start-planting")["ok"])
            views.robot.workflow_thread.join(timeout=5)
            self.assertEqual(views.robot.state.value, "complete")
            self.assertTrue(self.post("/api/start-monitoring")["ok"])
            if views.robot.monitoring_thread:
                views.robot.workflow_thread.join(timeout=5)
            state = self.client.get("/api/state").json()
            self.assertEqual(state["operation"]["status"], "completed")
            self.assertEqual(state["monitoring"]["completed"], 1)

    def test_load_seeds_accepts_required_counts_and_planting_consumes_them(self):
        with patch("spacefruit.hardware.time.sleep", return_value=None):
            self.post("/api/start")
            self.post("/api/add-plant", {"plant": "Tomato", "count": 2})
            self.post("/api/add-plant", {"plant": "Lettuce", "count": 1})
            self.post("/api/confirm")

            result = self.post("/api/load-seeds", {
                "counts": {"Tomato": 2, "Lettuce": 1},
            })
            self.assertTrue(result["ok"])
            self.assertEqual(result["loaded"], {"Tomato": 2, "Lettuce": 1})

            self.post("/api/start-planting")
            views.robot.workflow_thread.join(timeout=5)

            state = self.client.get("/api/state").json()
            self.assertEqual(state["state"], "complete")
            self.assertEqual(state["operation"]["status"], "completed")
            self.assertEqual(state["seed_count"], 0)
            self.assertTrue(all(c["status"] == "planted" for c in state["planting_cells"]))

    def test_planting_is_not_reported_complete_while_worker_is_running(self):
        with patch("spacefruit.hardware.time.sleep", return_value=None):
            self.post("/api/start")
            self.post("/api/add-plant", {"plant": "Tomato", "count": 1})
            self.post("/api/confirm")
            self.post("/api/load-seeds", {"counts": {"Tomato": 1}})
            original = views.robot.create_planting_plan
            def delayed_plan():
                import time
                time.sleep(0.15)
                original()
            views.robot.create_planting_plan = delayed_plan
            self.post("/api/start-planting")
            state = self.client.get("/api/state").json()
            self.assertEqual(state["operation"]["status"], "running")
            views.robot.monitoring_thread.join(timeout=5)
            state = self.client.get("/api/state").json()
            self.assertEqual(state["operation"]["status"], "completed")
            self.assertTrue(all(c["status"] == "planted" for c in state["planting_cells"]))

    def test_harvest_endpoint_checks_selected_profile_and_updates_robot_inventory(self):
        class ReadyCameraModel:
            def analyze(self, frame, profile):
                return HarvestAnalysis(True, "Camera confirms ripe.")

        with patch("spacefruit.hardware.time.sleep", return_value=None):
            self.post("/api/start")
            self.post("/api/add-plant", {"plant": "Tomato", "count": 1})
            self.post("/api/confirm")
            self.post("/api/load-seeds", {"counts": {"Tomato": 1}})
            self.post("/api/start-planting")
            views.robot.workflow_thread.join(timeout=5)
            profile_id = next(iter(views.robot.plant_profiles))
            views.robot.harvest_readiness_model = ReadyCameraModel()

            response = self.post("/api/harvest", {"profile_id": profile_id})
            views.robot.harvest_thread.join(timeout=5)

        self.assertTrue(response["ok"])
        state = self.client.get("/api/state").json()
        self.assertEqual(len(state["plant_profiles"]), 1)
        self.assertEqual(state["plant_profiles"][0]["plant_type"], "Empty Plot")
        self.assertEqual(state["planting_cells"][0]["status"], "empty_plot")
        self.assertEqual(state["harvest_inventory"], {"Tomato": 1})
        self.assertEqual(len(state["harvest_inventory_items"]), 1)
        self.assertEqual(state["harvest_inventory_items"][0]["plant_type"], "Tomato")
        self.assertEqual(state["harvest_inventory_items"][0]["quantity"], 1)
        self.assertTrue(state["harvest_inventory_items"][0]["img"])
        self.assertEqual(state["harvested_items"][0]["profile_id"], profile_id)

    def test_replant_endpoint_replaces_one_empty_plot_with_selected_plant(self):
        class ReadyCameraModel:
            def analyze(self, frame, profile):
                return HarvestAnalysis(True, "Camera confirms ripe.")

        with patch("spacefruit.hardware.time.sleep", return_value=None):
            self.post("/api/start")
            self.post("/api/add-plant", {"plant": "Tomato", "count": 1})
            self.post("/api/confirm")
            self.post("/api/load-seeds", {"counts": {"Tomato": 1}})
            self.post("/api/start-planting")
            views.robot.workflow_thread.join(timeout=5)
            old_profile_id = views.robot.planting_cells[0].profile_id
            views.robot.harvest_readiness_model = ReadyCameraModel()
            self.post("/api/harvest", {"profile_id": old_profile_id})
            views.robot.harvest_thread.join(timeout=5)
            empty_id = views.robot.planting_cells[0].profile_id

            response = self.post("/api/replant", {"profile_id": empty_id, "plant": "Cucumber"})
            views.robot.workflow_thread.join(timeout=5)

        self.assertTrue(response["ok"])
        state = self.client.get("/api/state").json()
        self.assertEqual(state["planting_cells"][0]["status"], "planted")
        self.assertEqual(state["planting_cells"][0]["plant"], "Cucumber")
        self.assertNotEqual(state["planting_cells"][0]["profile_id"], empty_id)
        self.assertEqual(state["plant_profiles"][0]["plant_type"], "Cucumber")


if __name__ == "__main__":
    unittest.main()
