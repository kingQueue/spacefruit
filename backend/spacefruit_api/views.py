import json
import math
import os
import threading
import uuid

from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from spacefruit.robot import FarmingRobot
from spacefruit.web import THUMBS_DIR

robot = FarmingRobot(start_server=False)
robot_lock = threading.RLock()
marketplace_listing_store = []


def _json(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _result(result):
    return JsonResponse(result, status=200 if result.get("ok") else 400)


def state(request):
    return JsonResponse(robot.api_state(), status=200)


def thumbnail(request, name):
    safe_name = name.replace("\\", "/")
    if not safe_name or safe_name.startswith("/") or ".." in safe_name.split("/"):
        return JsonResponse({"error": "invalid thumbnail path"}, status=400)
    path = os.path.realpath(os.path.join(THUMBS_DIR, safe_name))
    root = os.path.realpath(THUMBS_DIR)
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        return JsonResponse({"error": "thumbnail not found"}, status=404)
    return FileResponse(open(path, "rb"))


@csrf_exempt
def start_workflow(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock: return _result(robot.start_workflow())

@csrf_exempt
def add_plant(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock: return _result(robot.add_plant_to_plan(data.get("plant"), data.get("count", 1)))

@csrf_exempt
def remove_plant(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock: return _result(robot.remove_one_plant_from_plan(data.get("plant")))

@csrf_exempt
def confirm_plan(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock: return _result(robot.confirm_plan())

@csrf_exempt
def load_seeds(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock: return _result(robot.load_seeds(data.get("counts", {})))

@csrf_exempt
def start_planting(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock: return _result(robot.start_planting())

@csrf_exempt
def start_monitoring(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with robot_lock: return _result(robot.start_monitoring())

@csrf_exempt
def harvest(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock: return _result(robot.start_harvest(data.get("profile_id")))

@csrf_exempt
def replant(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with robot_lock: return _result(robot.start_replant(data.get("profile_id"), data.get("plant")))

@csrf_exempt
def marketplace_listings(request):
    if request.method == "GET":
        with robot_lock:
            return JsonResponse({"listings": list(marketplace_listing_store)}, status=200)
    if request.method != "POST": return JsonResponse({"ok": False, "error": "GET or POST required."}, status=405)
    data = _json(request)
    section = data.get("section")
    items = data.get("items")
    if section not in {"trade", "buy", "donate"}:
        return JsonResponse({"ok": False, "error": "Choose Trade, Buy, or Donate."}, status=400)
    if not isinstance(items, list) or not items:
        return JsonResponse({"ok": False, "error": "Select at least one item from your harvest inventory."}, status=400)

    with robot_lock:
        available = {item["plant_type"]: item for item in robot.harvest_inventory_items.values()}
        active_totals = {}
        for listing in marketplace_listing_store:
            if listing["active"]:
                active_totals[listing["plant_type"]] = active_totals.get(listing["plant_type"], 0) + listing["quantity"]

        requested = []
        requested_by_type = {}
        for item in items:
            if not isinstance(item, dict):
                return JsonResponse({"ok": False, "error": "Each selected item must include a plant type and quantity."}, status=400)
            plant_type = item.get("plant_type")
            try:
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError):
                return JsonResponse({"ok": False, "error": f"Enter a valid quantity for {plant_type or 'the selected plant'}."}, status=400)
            if not isinstance(plant_type, str) or plant_type not in available or quantity < 1:
                return JsonResponse({"ok": False, "error": "Choose a harvested plant and a quantity of at least one."}, status=400)
            try:
                weight = float(item.get("weight"))
            except (TypeError, ValueError):
                return JsonResponse({"ok": False, "error": f"Enter the weight for {plant_type}."}, status=400)
            weight_unit = item.get("weight_unit", "lb")
            if not math.isfinite(weight) or weight <= 0 or weight_unit not in {"lb", "oz", "kg", "g"}:
                return JsonResponse({"ok": False, "error": f"Enter a valid weight and unit for {plant_type}."}, status=400)
            asking_price = None
            if section == "buy":
                try:
                    asking_price = round(float(item.get("asking_price")), 2)
                except (TypeError, ValueError):
                    return JsonResponse({"ok": False, "error": f"Enter an asking price for {plant_type}."}, status=400)
                if not math.isfinite(asking_price) or asking_price <= 0:
                    return JsonResponse({"ok": False, "error": f"Asking price for {plant_type} must be greater than zero."}, status=400)
            requested.append({"plant_type": plant_type, "quantity": quantity, "weight": weight, "weight_unit": weight_unit, "asking_price": asking_price})
            requested_by_type[plant_type] = requested_by_type.get(plant_type, 0) + quantity
        for plant_type, quantity in requested_by_type.items():
            in_stock = available[plant_type]["quantity"] - active_totals.get(plant_type, 0)
            if quantity > in_stock:
                return JsonResponse({"ok": False, "error": f"Only {in_stock} {plant_type} available to list from your harvest inventory."}, status=400)

        created = []
        for item in requested:
            plant_type = item["plant_type"]
            listing = {
                "id": uuid.uuid4().hex[:12],
                "section": section,
                "plant_type": plant_type,
                "quantity": item["quantity"],
                "weight": item["weight"],
                "weight_unit": item["weight_unit"],
                "asking_price": item["asking_price"],
                "img": available[plant_type].get("img") or "default.svg",
                "grower": "Your garden",
                "location": "Your neighborhood",
                "active": True,
                "created_at": robot.now_iso(),
            }
            marketplace_listing_store.append(listing)
            created.append(listing)
    return JsonResponse({"ok": True, "listings": created}, status=200)

@csrf_exempt
def marketplace_listing_action(request, listing_id):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    action = _json(request).get("action")
    if action not in {"deactivate", "remove"}:
        return JsonResponse({"ok": False, "error": "Choose whether to deactivate or remove the listing."}, status=400)
    with robot_lock:
        listing = next((item for item in marketplace_listing_store if item["id"] == listing_id), None)
        if listing is None:
            return JsonResponse({"ok": False, "error": "Marketplace listing not found."}, status=404)
        if action == "remove":
            marketplace_listing_store.remove(listing)
        else:
            listing["active"] = False
    return JsonResponse({"ok": True}, status=200)
