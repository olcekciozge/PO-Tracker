"""Query-only helpers: keep all department scoping in one audited location."""

from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import User
from .permissions import can_view_roster, is_platform_admin


def visible_users_for(actor):
    """Return the only users this actor may list; never return all by default."""
    user_model = get_user_model()
    queryset = user_model.objects.all().order_by("username", "pk")
    if is_platform_admin(actor):
        return queryset
    if can_view_roster(actor):
        return queryset.filter(
            department_code=actor.department_code,
            role__in=(User.Role.STUDENT, User.Role.INSTRUCTOR),
            is_superuser=False,
        )
    return queryset.none()


def search_users(queryset, term="", role="", status=""):
    term = (term or "").strip()[:100]
    if term:
        queryset = queryset.filter(
            Q(username__icontains=term)
            | Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(email__icontains=term)
            | Q(student_number__icontains=term)
        )
    if role in User.Role.values:
        queryset = queryset.filter(role=role)
    if status == "active":
        queryset = queryset.filter(is_active=True)
    if status == "inactive":
        queryset = queryset.filter(is_active=False)
    return queryset


def role_totals_for(actor):
    queryset = visible_users_for(actor)
    return {role: queryset.filter(role=role).count() for role in User.Role.values}
