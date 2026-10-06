import json
import os
from urllib.parse import urlencode

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .signals import ensure_user_workspace

User = get_user_model()


def _json(request):
    try:
        return json.loads(request.body.decode("utf-8")) if request.body else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _user_payload(user):
    profile, garden = ensure_user_workspace(user)
    return {
        "id": user.pk,
        "email": user.email,
        "display_name": profile.display_name,
        "garden": {"id": garden.pk, "name": garden.name},
    }


@require_http_methods(["GET"])
@ensure_csrf_cookie
def auth_csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_http_methods(["GET"])
def auth_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=200)
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})


@require_http_methods(["GET"])
def auth_providers(request):
    return JsonResponse({"google": bool(os.environ.get("GOOGLE_OAUTH_CLIENT_ID") and os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"))})


@require_http_methods(["POST"])
def auth_register(request):
    data = _json(request)
    if data is None:
        return JsonResponse({"error": "Send valid JSON."}, status=400)
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    confirm = data.get("password_confirm", "")
    if not email or "@" not in email:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)
    if password != confirm:
        return JsonResponse({"error": "The passwords do not match."}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"error": "An account with that email already exists. Sign in or reset its password."}, status=400)
    try:
        validate_password(password)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)
    user = User.objects.create_user(username=email, email=email, password=password)
    ensure_user_workspace(user)
    login(request, user)
    request.session.save()
    return JsonResponse({"ok": True, "authenticated": True, "user": _user_payload(user)}, status=201)


@require_http_methods(["POST"])
def auth_login(request):
    data = _json(request)
    if data is None:
        return JsonResponse({"error": "Send valid JSON."}, status=400)
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    user = authenticate(request, username=email, password=password)
    if user is None:
        return JsonResponse({"error": "Email or password was not recognized."}, status=400)
    login(request, user)
    request.session.save()
    return JsonResponse({"ok": True, "authenticated": True, "user": _user_payload(user)})


@require_http_methods(["POST"])
def auth_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def auth_forgot_password(request):
    data = _json(request)
    if data is None:
        return JsonResponse({"error": "Send valid JSON."}, status=400)
    email = str(data.get("email", "")).strip().lower()
    users = User.objects.filter(email__iexact=email, is_active=True).exclude(password="") if email else []
    for user in users:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        query = urlencode({"uid": uid, "token": token})
        reset_url = f"{request.scheme}://{request.get_host()}/reset-password?{query}"
        send_mail(
            "Reset your SpaceFruit password",
            f"Use this one-time link to reset your SpaceFruit password:\n\n{reset_url}\n\nIf you did not request this, you can ignore this email.",
            None,
            [user.email],
            fail_silently=False,
        )
    return JsonResponse({"ok": True, "message": "If an account exists for that email, a password reset link has been sent."})


@require_http_methods(["POST"])
def auth_reset_password(request):
    data = _json(request)
    if data is None:
        return JsonResponse({"error": "Send valid JSON."}, status=400)
    try:
        uid = force_str(urlsafe_base64_decode(data.get("uid", "")))
        user = User.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return JsonResponse({"error": "This reset link is invalid or has expired."}, status=400)
    token = data.get("token", "")
    if not default_token_generator.check_token(user, token):
        return JsonResponse({"error": "This reset link is invalid or has expired."}, status=400)
    form = SetPasswordForm(user, {"new_password1": data.get("password", ""), "new_password2": data.get("password_confirm", "")})
    if not form.is_valid():
        return JsonResponse({"error": " ".join(form.errors.get("new_password1", form.non_field_errors())) or "Check the new password."}, status=400)
    form.save()
    return JsonResponse({"ok": True, "message": "Your password has been updated. You can now sign in."})
