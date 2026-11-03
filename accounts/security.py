"""Dependency-free login throttling (shared cache recommended in deployment)."""

import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache


def _failed_key(request, identifier):
    """Key hashed with SECRET_KEY: no raw identifiers or addresses in cache."""
    address = request.META.get("REMOTE_ADDR", "unknown")
    identifier = (identifier or "").strip().casefold()[:150]
    payload = f"{address}|{identifier}".encode("utf-8", errors="replace")
    digest = hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()
    return f"accounts:login:failed:{digest}"


def failure_limit():
    return max(1, int(getattr(settings, "ACCOUNTS_LOGIN_FAILURE_LIMIT", 8)))


def failure_window():
    return max(60, int(getattr(settings, "ACCOUNTS_LOGIN_FAILURE_WINDOW", 900)))


def is_login_blocked(request, identifier):
    return int(cache.get(_failed_key(request, identifier), 0)) >= failure_limit()


def record_login_failure(request, identifier):
    key = _failed_key(request, identifier)
    # This get/set is sufficient for a classroom demo; for high concurrency a
    # shared atomic cache/rate limiter should be used at the proxy/edge layer.
    attempts = int(cache.get(key, 0)) + 1
    cache.set(key, attempts, timeout=failure_window())
    return attempts


def clear_login_failures(request, identifier):
    cache.delete(_failed_key(request, identifier))
