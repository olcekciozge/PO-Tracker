"""Transactional account management: the only place business mutations occur."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import AuditLog, User
from .permissions import can_assign_role, can_manage_target


MANAGED_FIELDS = (
    "first_name", "last_name", "email", "role", "student_number", "department_code"
)


def log_event(*, actor, target, action, metadata=None):
    """Avoid free-form request data in audit metadata to prevent secret leaks."""
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        target=target if getattr(target, "pk", None) else None,
        action=action,
        metadata=metadata or {},
    )


def _require_manager(actor, target=None):
    if not can_manage_target(actor, target):
        raise PermissionDenied("Bu hesap üzerinde işlem yapamazsınız.")


@transaction.atomic
def create_account(*, actor, form):
    """Create an account from a prevalidated form and audit its assigned role."""
    _require_manager(actor)
    if not form.is_valid():
        raise ValidationError("Hesap formu geçerli değil.")
    new_user = form.save(commit=False)
    if not can_assign_role(actor, new_user.role):
        raise PermissionDenied("Seçilen rolü atama yetkiniz yok.")
    new_user.is_staff = bool(new_user.role == User.Role.ADMIN and actor.is_superuser)
    new_user.is_superuser = False
    new_user.full_clean()
    new_user.save()
    log_event(
        actor=actor, target=new_user, action=AuditLog.Action.USER_CREATED,
        metadata={"role": new_user.role},
    )
    return new_user


@transaction.atomic
def update_account(*, actor, target, form):
    """Update allowlisted fields, not password / is_staff / is_superuser."""
    _require_manager(actor, target)
    if not form.is_valid():
        raise ValidationError("Hesap formu geçerli değil.")
    original = User.objects.select_for_update().get(pk=target.pk)
    previous = {key: getattr(original, key) for key in MANAGED_FIELDS}
    user = form.save(commit=False)
    if not can_assign_role(actor, user.role):
        raise PermissionDenied("Seçilen rolü atama yetkiniz yok.")
    if original.is_superuser and user.role != User.Role.ADMIN:
        raise PermissionDenied("Süper kullanıcı rolü değiştirilemez.")
    # Staff is deliberately not a public form field. Only a superuser may
    # promote an account to platform administrator through this service.
    user.is_staff = bool(user.role == User.Role.ADMIN and actor.is_superuser)
    user.is_superuser = original.is_superuser
    user.is_active = original.is_active
    user.full_clean()
    user.save()
    changed = sorted(
        key for key in MANAGED_FIELDS if previous[key] != getattr(user, key)
    )
    if changed:
        log_event(
            actor=actor, target=user, action=AuditLog.Action.USER_UPDATED,
            metadata={"fields": changed, "role": user.role},
        )
    return user


@transaction.atomic
def set_account_active(*, actor, target, active):
    """Disable login without deleting grades or violating self-protection."""
    _require_manager(actor, target)
    user = User.objects.select_for_update().get(pk=target.pk)
    active = bool(active)
    if user.is_superuser and not active:
        remaining = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=user.pk)
        if not remaining.exists():
            raise PermissionDenied("Son aktif süper kullanıcı pasifleştirilemez.")
    if user.is_active == active:
        return user
    user.is_active = active
    user.save(update_fields=["is_active"])
    log_event(
        actor=actor, target=user,
        action=AuditLog.Action.USER_ACTIVATED if active else AuditLog.Action.USER_DEACTIVATED,
    )
    return user


@transaction.atomic
def update_own_profile(*, actor, form):
    if not getattr(actor, "is_authenticated", False) or not actor.is_active:
        raise PermissionDenied("Giriş yapmanız gerekiyor.")
    if form.instance.pk != actor.pk:
        raise PermissionDenied("Başka kullanıcının profili değiştirilemez.")
    if not form.is_valid():
        raise ValidationError("Profil formu geçerli değil.")
    user = form.save(commit=False)
    user.full_clean()
    user.save(update_fields=["first_name", "last_name", "email"])
    if form.changed_data:
        log_event(
            actor=actor, target=actor, action=AuditLog.Action.PROFILE_UPDATED,
            metadata={"fields": sorted(form.changed_data)},
        )
    return user
