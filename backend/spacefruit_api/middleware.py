import hashlib
import os
import threading
import time
from types import SimpleNamespace

import requests
from django.http import JsonResponse

from spacefruit.robot import FarmingRobot

_robots = {}
_locks = {}
_registry_lock = threading.RLock()
_auth_cache = {}
_auth_cache_lock = threading.RLock()
_AUTH_CACHE_SECONDS = 45


def _supabase_user(token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = time.monotonic()
    with _auth_cache_lock:
        cached = _auth_cache.get(token_hash)
        if cached and cached[0] > now:
            return cached[1], None

    base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    if not base_url or not publishable_key:
        return None, "Supabase is not configured on the backend."
    try:
        response = requests.get(
            f"{base_url}/auth/v1/user",
            headers={"apikey": publishable_key, "Authorization": f"Bearer {token}"},
            timeout=5,
        )
    except requests.RequestException:
        return None, "Could not verify your Supabase session. Try again shortly."
    if response.status_code == 401:
        return None, None
    if response.status_code != 200:
        return None, "Supabase could not verify your session."
    payload = response.json()
    user_id = payload.get("id")
    if not user_id:
        return None, None
    user = SimpleNamespace(
        id=user_id,
        pk=user_id,
        email=payload.get("email", ""),
        user_metadata=payload.get("user_metadata") or {},
        is_authenticated=True,
    )
    with _auth_cache_lock:
        if len(_auth_cache) > 2048:
            for key, value in list(_auth_cache.items()):
                if value[0] <= now:
                    _auth_cache.pop(key, None)
        _auth_cache[token_hash] = (now + _AUTH_CACHE_SECONDS, user)
    return user, None


class LoginRequiredAPIMiddleware:
    """Verify Supabase access tokens and attach isolated simulated robot state."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JsonResponse({"error": "Sign in to use your garden."}, status=401)
        token = authorization[7:].strip()
        if not token:
            return JsonResponse({"error": "Sign in to use your garden."}, status=401)
        user, error = _supabase_user(token)
        if error:
            return JsonResponse({"error": error}, status=503)
        if user is None:
            return JsonResponse({"error": "Your session has expired. Please sign in again."}, status=401)
        request.supabase_access_token = token
        request.supabase_user_id = user.id
        request.user = user
        with _registry_lock:
            if user.id not in _robots:
                _robots[user.id] = FarmingRobot(start_server=False)
                _locks[user.id] = threading.RLock()
            request.robot = _robots[user.id]
            request.robot_lock = _locks[user.id]
        return self.get_response(request)
