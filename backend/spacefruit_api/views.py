import json
import math
import os
import threading
import requests
from django.http import FileResponse, JsonResponse

from spacefruit.robot import FarmingRobot
from spacefruit.web import THUMBS_DIR

robot = FarmingRobot(start_server=False)  # Retained for direct development introspection only.
robot_lock = threading.RLock()
_persisted_signatures = {}
_garden_ids = {}


class SupabaseDataError(RuntimeError):
    pass


def _supabase_rest(request, method, table, *, params=None, payload=None, prefer=None):
    base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    if not base_url or not publishable_key:
        raise SupabaseDataError("Supabase is not configured on the backend.")
    headers = {
        "apikey": publishable_key,
        "Authorization": f"Bearer {request.supabase_access_token}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    try:
        response = requests.request(
            method, f"{base_url}/rest/v1/{table}", headers=headers,
            params=params, json=payload, timeout=8,
        )
    except requests.RequestException as exc:
        raise SupabaseDataError("Could not reach the Supabase database.") from exc
    if response.status_code >= 400:
        try:
            details = response.json().get("message") or response.json().get("hint")
        except ValueError:
            details = None
        raise SupabaseDataError(details or "Supabase rejected the database request.")
    return response.json() if response.content else []


def _user_garden(request):
    if request.supabase_user_id in _garden_ids:
        return _garden_ids[request.supabase_user_id]
    rows = _supabase_rest(request, "GET", "gardens", params={
        "select": "id,location_label", "owner_id": f"eq.{request.supabase_user_id}", "limit": "1",
    })
    if not rows:
        rows = _supabase_rest(request, "POST", "gardens", payload={
            "owner_id": request.supabase_user_id,
        }, prefer="return=representation")
    if not rows:
        raise SupabaseDataError("No garden is available for this account.")
    garden = rows[0]
    _garden_ids[request.supabase_user_id] = garden
    return garden


def _persist_robot_state(request, state):
    revision = state.get("state_revision")
    signature = (revision, len(state.get("planting_cells", [])), len(state.get("harvest_inventory_items", [])))
    if _persisted_signatures.get(request.supabase_user_id) == signature:
        return
    garden = _user_garden(request)
    profiles = {profile.get("profile_id"): profile for profile in state.get("plant_profiles", [])}
    plots = []
    for cell in state.get("planting_cells", []):
        profile = profiles.get(cell.get("profile_id"), {})
        status = cell.get("status", "empty")
        if status not in {"planted", "harvested"}:
            status = "empty"
        plots.append({
            "garden_id": garden["id"],
            "label": f"{int(cell.get('row', 0)) + 1}-{int(cell.get('column', 0)) + 1}",
            "plant_type": cell.get("plant") or "",
            "status": status,
            "health_status": profile.get("health_status", ""),
            "health_issues": profile.get("health_issues") or [],
            "planted_at": profile.get("planted_at") or None,
            "last_monitored_at": profile.get("last_monitored_at") or None,
        })
    if plots:
        _supabase_rest(request, "POST", "garden_plots", params={"on_conflict": "garden_id,label"},
                       payload=plots, prefer="resolution=merge-duplicates")
    inventory = [{
        "garden_id": garden["id"], "plant_type": item.get("plant_type", ""),
        "quantity": int(item.get("quantity", 0)), "image_path": item.get("img") or "",
    } for item in state.get("harvest_inventory_items", []) if item.get("plant_type")]
    if inventory:
        _supabase_rest(request, "POST", "harvest_inventory_items", params={"on_conflict": "garden_id,plant_type"},
                       payload=inventory, prefer="resolution=merge-duplicates")
    _persisted_signatures[request.supabase_user_id] = signature


def _json(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _result(result):
    return JsonResponse(result, status=200 if result.get("ok") else 400)


def state(request):
    payload = request.robot.api_state()
    try:
        _persist_robot_state(request, payload)
    except SupabaseDataError as exc:
        payload["storage_error"] = str(exc)
    return JsonResponse(payload, status=200)


def thumbnail(request, name):
    safe_name = name.replace("\\", "/")
    if not safe_name or safe_name.startswith("/") or ".." in safe_name.split("/"):
        return JsonResponse({"error": "invalid thumbnail path"}, status=400)
    path = os.path.realpath(os.path.join(THUMBS_DIR, safe_name))
    root = os.path.realpath(THUMBS_DIR)
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        return JsonResponse({"error": "thumbnail not found"}, status=404)
    return FileResponse(open(path, "rb"))


def start_workflow(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with request.robot_lock: return _result(request.robot.start_workflow())

def add_plant(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with request.robot_lock: return _result(request.robot.add_plant_to_plan(data.get("plant"), data.get("count", 1)))

def remove_plant(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with request.robot_lock: return _result(request.robot.remove_one_plant_from_plan(data.get("plant")))

def confirm_plan(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with request.robot_lock: return _result(request.robot.confirm_plan())

def load_seeds(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with request.robot_lock: return _result(request.robot.load_seeds(data.get("counts", {})))

def start_planting(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with request.robot_lock: return _result(request.robot.start_planting())

def start_monitoring(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    with request.robot_lock: return _result(request.robot.start_monitoring())

def harvest(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with request.robot_lock: return _result(request.robot.start_harvest(data.get("profile_id")))

def replant(request):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    data = _json(request)
    with request.robot_lock: return _result(request.robot.start_replant(data.get("profile_id"), data.get("plant")))

def marketplace_listings(request):
    if request.method == "GET":
        try:
            rows = _supabase_rest(request, "GET", "marketplace_listings", params={
                "select": "*", "order": "created_at.desc",
            })
        except SupabaseDataError as exc:
            return JsonResponse({"error": str(exc)}, status=503)
        return JsonResponse({"listings": [{
            "id": row["id"], "section": row["section"], "plant_type": row["plant_type"],
            "quantity": row["quantity"], "weight": float(row["weight"]), "weight_unit": row["weight_unit"],
            "asking_price": float(row["asking_price"]) if row["asking_price"] is not None else None,
            "img": row["image_path"] or "default.svg", "grower": row["grower_label"] or "SpaceFruit grower",
            "location": row["location_label"] or "Community garden", "active": row["active"],
            "created_at": row["created_at"], "is_mine": row["owner_id"] == request.supabase_user_id,
        } for row in rows]}, status=200)
    if request.method != "POST": return JsonResponse({"ok": False, "error": "GET or POST required."}, status=405)
    data = _json(request)
    section = data.get("section")
    items = data.get("items")
    if section not in {"trade", "buy", "donate"}:
        return JsonResponse({"ok": False, "error": "Choose Trade, Buy, or Donate."}, status=400)
    if not isinstance(items, list) or not items:
        return JsonResponse({"ok": False, "error": "Select at least one item from your harvest inventory."}, status=400)

    with request.robot_lock:
        available = {item["plant_type"]: item for item in request.robot.harvest_inventory_items.values()}
        active_totals = {}
        try:
            garden = _user_garden(request)
            existing = _supabase_rest(request, "GET", "marketplace_listings", params={
                "select": "plant_type,quantity", "owner_id": f"eq.{request.supabase_user_id}",
                "active": "eq.true",
            })
        except SupabaseDataError as exc:
            return JsonResponse({"error": str(exc)}, status=503)
        for listing in existing:
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
        grower_label = request.user.user_metadata.get("full_name") or request.user.email.split("@")[0]
        for item in requested:
            plant_type = item["plant_type"]
            try:
                rows = _supabase_rest(request, "POST", "marketplace_listings", payload={
                    "owner_id": request.supabase_user_id, "garden_id": garden["id"],
                    "section": section, "plant_type": plant_type, "quantity": item["quantity"],
                    "weight": item["weight"], "weight_unit": item["weight_unit"],
                    "asking_price": item["asking_price"],
                    "image_path": available[plant_type].get("img") or "default.svg",
                    "grower_label": grower_label, "location_label": garden.get("location_label") or "Community garden",
                }, prefer="return=representation")
            except SupabaseDataError as exc:
                return JsonResponse({"error": str(exc)}, status=503)
            if rows:
                row = rows[0]
                created.append({"id": row["id"], "section": section, "plant_type": plant_type,
                    "quantity": row["quantity"], "weight": float(row["weight"]), "weight_unit": row["weight_unit"],
                    "asking_price": float(row["asking_price"]) if row["asking_price"] is not None else None,
                    "img": row["image_path"], "grower": row["grower_label"],
                    "location": row["location_label"], "active": True,
                    "created_at": row["created_at"], "is_mine": True})
    return JsonResponse({"ok": True, "listings": created}, status=200)

def marketplace_listing_action(request, listing_id):
    if request.method != "POST": return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    action = _json(request).get("action")
    if action not in {"deactivate", "remove"}:
        return JsonResponse({"ok": False, "error": "Choose whether to deactivate or remove the listing."}, status=400)
    filters = {"id": f"eq.{listing_id}", "owner_id": f"eq.{request.supabase_user_id}"}
    try:
        if action == "remove":
            rows = _supabase_rest(request, "DELETE", "marketplace_listings", params=filters, prefer="return=representation")
        else:
            rows = _supabase_rest(request, "PATCH", "marketplace_listings", params=filters,
                                  payload={"active": False}, prefer="return=representation")
    except SupabaseDataError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    if not rows:
        return JsonResponse({"ok": False, "error": "Marketplace listing not found."}, status=404)
    return JsonResponse({"ok": True}, status=200)
