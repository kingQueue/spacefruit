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

            if views.robot.monitoring_thread:
                thread.join(timeout=5)

            state = self.client.get("/api/state").json()
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
            if views.robot.monitoring_thread:
                views.robot.monitoring_thread.join(timeout=5)
            self.assertEqual(views.robot.state.value, "complete")
            self.assertTrue(self.post("/api/start-monitoring")["ok"])
            if views.robot.monitoring_thread:
                views.robot.monitoring_thread.join(timeout=5)
            state = self.client.get("/api/state").json()
            self.assertEqual(state["operation"]["status"], "completed")
            self.assertEqual(state["monitoring"]["completed"], 1)

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


if __name__ == "__main__":
    unittest.main()
