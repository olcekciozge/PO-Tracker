"""Reusable role gates. Per-course/grade object filtering is NOT provided here."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import User


def is_active_user(user):
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "is_active", False))


def is_platform_admin(user):
    """Superusers or active admin-role staff can administer app identities."""
    return is_active_user(user) and bool(
        user.is_superuser or (user.role == User.Role.ADMIN and user.is_staff)
    )


def has_role(user, *roles):
    """A valid role, with the platform admin permitted to view any role page."""
    if not is_active_user(user):
        return False
    # A role value of 'admin' must never be enough to bypass staff checks.
    if user.role == User.Role.ADMIN:
        return is_platform_admin(user)
    return is_platform_admin(user) or user.role in roles


def can_manage_target(actor, target=None):
    """App staff cannot edit admins/superusers; nobody may edit self here."""
    if not is_platform_admin(actor):
        return False
    if target is None:
        return True
    if actor.pk == target.pk:
        return False
    if target.is_superuser or target.role == User.Role.ADMIN:
        return bool(actor.is_superuser)
    return True


def can_assign_role(actor, role):
    if not is_platform_admin(actor):
        return False
    if role not in User.Role.values:
        return False
    return role != User.Role.ADMIN or actor.is_superuser


def can_view_user(actor, target):
    if not is_active_user(actor):
        return False
    if actor.pk == target.pk:
        return True
    if is_platform_admin(actor):
        return True
    return bool(
        actor.role == User.Role.HEAD
        and actor.department_code
        and target.department_code == actor.department_code
        and target.role in (User.Role.STUDENT, User.Role.INSTRUCTOR)
        and not target.is_superuser
    )


def can_view_roster(user):
    return is_platform_admin(user) or bool(
        is_active_user(user) and user.role == User.Role.HEAD and user.department_code
    )


def role_required(*roles):
    """Redirect anonymous requests to login; return HTTP 403 for wrong role."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def protected_view(request, *args, **kwargs):
            if not has_role(request.user, *roles):
                raise PermissionDenied("Bu sayfaya erişim yetkiniz bulunmuyor.")
            return view_func(request, *args, **kwargs)
        return protected_view
    return decorator


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not has_role(request.user, *self.allowed_roles):
            raise PermissionDenied("Bu sayfaya erişim yetkiniz bulunmuyor.")
        return super().dispatch(request, *args, **kwargs)


class PlatformAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not is_platform_admin(request.user):
            raise PermissionDenied("Yalnızca hesap yöneticileri erişebilir.")
        return super().dispatch(request, *args, **kwargs)
