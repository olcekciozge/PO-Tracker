"""Authentication lifecycle audit; no passwords, secrets or IPs are stored."""

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import AuditLog


@receiver(user_logged_in, dispatch_uid="accounts_audit_user_logged_in")
def record_login(sender, request, user, **kwargs):
    if user and user.pk:
        AuditLog.objects.create(actor=user, target=user, action=AuditLog.Action.LOGIN)


@receiver(user_logged_out, dispatch_uid="accounts_audit_user_logged_out")
def record_logout(sender, request, user, **kwargs):
    if user and user.pk:
        AuditLog.objects.create(actor=user, target=user, action=AuditLog.Action.LOGOUT)
