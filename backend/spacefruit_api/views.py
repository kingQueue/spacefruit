import json
import threading

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from spacefruit.robot import FarmingRobot

robot = FarmingRobot(start_server=False)
robot_lock = threading.RLock()


def _json(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _result(result):
    return JsonResponse(result, status=200 if result.get("ok") else 400)


def state(request):
    return JsonResponse(robot.api_state(), status=200)


@csrf_exempt
def start_workflow(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock:
        return _result(robot.start_workflow())


@csrf_exempt
def add_plant(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock:
        return _result(robot.add_plant_to_plan(data.get("plant"), data.get("count", 1)))


@csrf_exempt
def remove_plant(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock:
        return _result(robot.remove_one_plant_from_plan(data.get("plant")))


@csrf_exempt
def confirm_plan(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock:
        return _result(robot.confirm_plan())


@csrf_exempt
def load_seeds(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock:
        return _result(robot.load_seeds(data.get("counts", {})))


@csrf_exempt
def start_planting(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock:
        return _result(robot.start_planting())


@csrf_exempt
def start_monitoring(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock:
        return _result(robot.start_monitoring())
