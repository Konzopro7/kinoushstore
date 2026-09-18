"""Password + encrypted TOTP protection for the Django administration."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .models import AdminLoginAttempt, AdminTwoFactorDevice, AdminTwoFactorRecoveryCode

MAX_FAILURES = 5
LOCKOUT_MINUTES = 15
SESSION_KEY = "pending_admin_2fa_user_id"
VERIFIED_SESSION_KEY = "admin_2fa_verified_user_id"


def _cipher():
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def _new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _encrypt(secret):
    return _cipher().encrypt(secret.encode("ascii")).decode("ascii")


def _decrypt(token):
    try:
        return _cipher().decrypt(token.encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError, TypeError):
        return ""


def _totp(secret, counter=None):
    counter = int(time.time() // 30) if counter is None else counter
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000
    return f"{value:06d}"


def _valid_totp(secret, code):
    if not secret or not (code or "").isdigit() or len(code) != 6:
        return False
    current = int(time.time() // 30)
    return any(hmac.compare_digest(_totp(secret, current + offset), code) for offset in (-1, 0, 1))


def _client_ip(request):
    return request.META.get("REMOTE_ADDR") or "0.0.0.0"


def admin_has_permission(request):
    """Deny admin access unless this exact session completed TOTP verification."""
    return bool(
        request.user.is_active
        and request.user.is_staff
        and request.session.get(VERIFIED_SESSION_KEY) == request.user.pk
    )


def _attempt(username, request):
    return AdminLoginAttempt.objects.get_or_create(username=username[:150], ip_address=_client_ip(request))[0]


def _is_locked(username, request):
    attempt = AdminLoginAttempt.objects.filter(username=username[:150], ip_address=_client_ip(request)).first()
    return bool(attempt and attempt.locked_until and attempt.locked_until > timezone.now())


def _record_failure(username, request):
    attempt = _attempt(username, request)
    attempt.failures += 1
    if attempt.failures >= MAX_FAILURES:
        attempt.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
    attempt.save(update_fields=("failures", "locked_until", "updated_at"))


def _clear_failures(username, request):
    AdminLoginAttempt.objects.filter(username=username[:150], ip_address=_client_ip(request)).delete()


def _pending_user(request):
    user_id = request.session.get(SESSION_KEY)
    return User.objects.filter(pk=user_id, is_active=True, is_staff=True).first()


def _start_pending_session(request, user):
    request.session.cycle_key()
    request.session[SESSION_KEY] = user.pk
    request.session.set_expiry(300)


@never_cache
@csrf_protect
def admin_login(request, extra_context=None):
    if request.user.is_authenticated and request.user.is_staff:
        if admin_has_permission(request):
            return redirect("admin:index")
        logout(request)
    username = request.POST.get("username", "") if request.method == "POST" else ""
    form = AdminAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        if _is_locked(username, request):
            form.add_error(None, "Trop de tentatives. Réessayez dans 15 minutes.")
        elif form.is_valid():
            user = form.get_user()
            _clear_failures(user.get_username(), request)
            _start_pending_session(request, user)
            device, _ = AdminTwoFactorDevice.objects.get_or_create(user=user)
            return redirect("admin_2fa_setup" if not device.is_confirmed else "admin_2fa_verify")
        else:
            _record_failure(username, request)
    return render(request, "admin/two_factor_login.html", {"form": form, **(extra_context or {})})


@never_cache
@csrf_protect
def setup_totp(request):
    user = _pending_user(request)
    if not user:
        return redirect("admin:login")
    device, _ = AdminTwoFactorDevice.objects.get_or_create(user=user)
    secret = _decrypt(device.encrypted_secret)
    if not secret:
        secret = _new_secret()
        device.encrypted_secret = _encrypt(secret)
        device.save(update_fields=("encrypted_secret",))
    if request.method == "POST":
        code = request.POST.get("code", "").replace(" ", "")
        if _valid_totp(secret, code):
            device.is_confirmed = True
            device.confirmed_at = timezone.now()
            device.save(update_fields=("is_confirmed", "confirmed_at"))
            plain_codes = [secrets.token_urlsafe(6).upper() for _ in range(8)]
            AdminTwoFactorRecoveryCode.objects.filter(device=device).delete()
            AdminTwoFactorRecoveryCode.objects.bulk_create([
                AdminTwoFactorRecoveryCode(device=device, code_hash=make_password(code)) for code in plain_codes
            ])
            request.session["admin_2fa_recovery_codes"] = plain_codes
            return redirect("admin_2fa_recovery_codes")
        messages.error(request, "Le code n’est pas valide. Vérifiez l’heure de votre téléphone puis réessayez.")
    return render(request, "admin/two_factor_setup.html", {
        "secret": secret,
        "account_name": user.get_username(),
    })


@never_cache
@csrf_protect
def verify_totp(request):
    user = _pending_user(request)
    if not user:
        return redirect("admin:login")
    device = AdminTwoFactorDevice.objects.filter(user=user, is_confirmed=True).first()
    if not device:
        return redirect("admin_2fa_setup")
    if request.method == "POST":
        code = request.POST.get("code", "").replace(" ", "")
        if _is_locked(user.get_username(), request):
            messages.error(request, "Trop de tentatives. Réessayez dans 15 minutes.")
        else:
            secret = _decrypt(device.encrypted_secret)
            recovery_code = next((item for item in device.recovery_codes.all() if check_password(code, item.code_hash)), None)
            if _valid_totp(secret, code) or recovery_code:
                if recovery_code:
                    recovery_code.delete()
                _clear_failures(user.get_username(), request)
                request.session.pop(SESSION_KEY, None)
                request.session.pop("admin_2fa_recovery_codes", None)
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                request.session[VERIFIED_SESSION_KEY] = user.pk
                return redirect(request.POST.get("next") or "admin:index")
            _record_failure(user.get_username(), request)
            messages.error(request, "Code invalide.")
    return render(request, "admin/two_factor_verify.html")


@never_cache
def recovery_codes(request):
    user = _pending_user(request)
    codes = request.session.get("admin_2fa_recovery_codes")
    if not user or not codes:
        return HttpResponseForbidden("Cette page n’est plus disponible.")
    if request.method == "POST":
        request.session.pop(SESSION_KEY, None)
        request.session.pop("admin_2fa_recovery_codes", None)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session[VERIFIED_SESSION_KEY] = user.pk
        return redirect("admin:index")
    return render(request, "admin/two_factor_recovery_codes.html", {"codes": codes})
