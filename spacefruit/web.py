"""Local HTTP control server and HTML template renderer."""

from __future__ import annotations

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote, urlparse

from .catalog import PLANT_CATALOG

APP_HOST = "127.0.0.1"
APP_PORT = 8080
THUMBS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "thumbs")
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")

def render_app() -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as template:
        html = template.read()
    catalog_options = "".join(
        f'<option value="{plant.name}">{plant.name}</option>'
        for plant in PLANT_CATALOG
    )
    return html.replace("{{CATALOG_OPTIONS}}", catalog_options)

class AppServer:
    def __init__(self, robot: "FarmingRobot", host: str = APP_HOST, port: int = APP_PORT):
        self.robot = robot
        self.host = host
        self.port = port
        self.server = HTTPServer((host, port), self._handler_class())

    def _handler_class(self):
        robot = self.robot

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, payload: dict, status: int = 200):
                body = json.dumps(payload, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self) -> dict:
                length = int(self.headers.get("Content-Length", "0"))
                if length == 0:
                    return {}
                raw = self.rfile.read(length).decode("utf-8")
                return json.loads(raw)

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/api/state":
                    self._send_json(robot.api_state())
                    return
                if path == "/":
                    self._send_html(render_app())
                    return
                if path.startswith("/thumbs/"):
                    self._send_thumbnail(path)
                    return
                self._send_json({"error": "not found"}, 404)

            def _send_thumbnail(self, path: str):
                requested_name = unquote(path[len("/thumbs/"):]).replace("\\", "/")
                if not requested_name or requested_name.startswith("/") or any(part in {"", ".", ".."} for part in requested_name.split("/")):
                    self._send_json({"error": "invalid thumbnail path"}, 400)
                    return

                thumbnail_path = os.path.realpath(os.path.join(THUMBS_DIR, requested_name))
                thumbs_root = os.path.realpath(THUMBS_DIR)
                if thumbnail_path != thumbs_root and not thumbnail_path.startswith(thumbs_root + os.sep):
                    self._send_json({"error": "invalid thumbnail path"}, 400)
                    return
                if not os.path.isfile(thumbnail_path):
                    self._send_json({"error": "thumbnail not found"}, 404)
                    return

                try:
                    with open(thumbnail_path, "rb") as image_file:
                        body = image_file.read()
                except OSError:
                    self._send_json({"error": "unable to read thumbnail"}, 500)
                    return

                content_type = mimetypes.guess_type(thumbnail_path)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=3600")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self, html: str):
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                path = urlparse(self.path).path
                try:
                    data = self._read_json()
                    if path == "/api/add-plant":
                        result = robot.add_plant_to_plan(data.get("plant"), data.get("count", 1))
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    if path == "/api/remove-plant":
                        result = robot.remove_one_plant_from_plan(data.get("plant"))
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    if path == "/api/confirm":
                        result = robot.confirm_plan()
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    if path == "/api/load-seeds":
                        result = robot.load_seeds(data.get("counts", {}))
                        self._send_json(result, 200 if result["ok"] else 400)
                        return
                    self._send_json({"error": "not found"}, 404)
                except Exception as exc:
                    self._send_json({"ok": False, "error": str(exc)}, 400)

            def log_message(self, format, *args):
                return

        return Handler

    def start(self):
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        print(f"[APP] Local control app running at http://{self.host}:{self.port}")

    def stop(self):
        self.server.shutdown()


