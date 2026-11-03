"""Accounts UI: secure authentication, profiles, manager workflows, rosters."""

import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView,
    PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    AccountCreateForm, AccountUpdateForm, LoginForm, ProfileForm, UserSearchForm,
)
from .models import AuditLog, User
from .permissions import (
    can_manage_target, can_view_roster, can_view_user, is_platform_admin,
)
from .security import (
    clear_login_failures, failure_window, is_login_blocked, record_login_failure,
)
from .selectors import role_totals_for, search_users, visible_users_for
from .services import create_account, log_event, set_account_active, update_account, update_own_profile


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        identifier = request.POST.get("username", "")
        if is_login_blocked(request, identifier):
            response = self.render_to_response(self.get_context_data(form=self.get_form()))
            response.status_code = 429
            response["Retry-After"] = str(failure_window())
            return response
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        record_login_failure(self.request, self.request.POST.get("username", ""))
        messages.error(self.request, "Kullanıcı adı veya parola hatalı.")
        return super().form_invalid(form)

    def form_valid(self, form):
        clear_login_failures(self.request, self.request.POST.get("username", ""))
        return super().form_valid(form)


class AccountLogoutView(LogoutView):
    # Django 5 requires a POST for logout; forms include {% csrf_token %}.
    next_page = reverse_lazy("accounts:login")


class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_event(
            actor=self.request.user,
            target=self.request.user,
            action=AuditLog.Action.PASSWORD_CHANGED,
        )
        return response


class AccountPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


class AccountPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


@login_required
def home(request):
    """Role-aware landing page; NOT a replacement for the analytics dashboard."""
    user = request.user
    totals = role_totals_for(user) if can_view_roster(user) else {}
    context = {
        "is_manager": is_platform_admin(user),
        "can_see_roster": can_view_roster(user),
        "role_stats": [
            {"label": label, "count": totals.get(role, 0)}
            for role, label in User.Role.choices
        ],
    }
    return render(request, "accounts/home.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            update_own_profile(actor=request.user, form=form)
            messages.success(request, "Profiliniz güncellendi.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


def _require_roster_viewer(request):
    if not can_view_roster(request.user):
        raise PermissionDenied("Kullanıcı listesine erişim yetkiniz bulunmuyor.")


def _require_platform_manager(request, target=None):
    if not can_manage_target(request.user, target):
        raise PermissionDenied("Kullanıcı yönetimi için yetkiniz bulunmuyor.")


def _filtered_roster(request):
    search_form = UserSearchForm(request.GET)
    queryset = visible_users_for(request.user)
    if search_form.is_valid():
        filters = search_form.cleaned_data
        queryset = search_users(
            queryset, filters.get("q"), filters.get("role"), filters.get("status")
        )
    return queryset, search_form


@login_required
@require_http_methods(["GET"])
def user_list(request):
    _require_roster_viewer(request)
    queryset, search_form = _filtered_roster(request)
    paginator = Paginator(queryset, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/user_list.html", {
        "page_obj": page,
        "search_form": search_form,
        "can_manage": is_platform_admin(request.user),
        "total_users": page.paginator.count,
    })


@login_required
@require_http_methods(["GET"])
def user_detail(request, pk):
    target = get_object_or_404(User, pk=pk)
    if not can_view_user(request.user, target):
        raise PermissionDenied("Bu kullanıcıyı görüntüleyemezsiniz.")
    return render(request, "accounts/user_detail.html", {
        "target": target,
        "can_manage": can_manage_target(request.user, target),
    })


@login_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    _require_platform_manager(request)
    if request.method == "POST":
        form = AccountCreateForm(request.POST, actor=request.user)
        if form.is_valid():
            target = create_account(actor=request.user, form=form)
            messages.success(request, f"{target.username} hesabı oluşturuldu.")
            return redirect("accounts:user_detail", pk=target.pk)
    else:
        form = AccountCreateForm(actor=request.user)
    return render(request, "accounts/user_form.html", {
        "form": form,
        "heading": "Kullanıcı oluştur",
        "submit_label": "Hesabı oluştur",
        "is_creation": True,
    })


@login_required
@require_http_methods(["GET", "POST"])
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    _require_platform_manager(request, target)
    if request.method == "POST":
        form = AccountUpdateForm(request.POST, instance=target, actor=request.user)
        if form.is_valid():
            target = update_account(actor=request.user, target=target, form=form)
            messages.success(request, "Kullanıcı bilgileri güncellendi.")
            return redirect("accounts:user_detail", pk=target.pk)
    else:
        form = AccountUpdateForm(instance=target, actor=request.user)
    return render(request, "accounts/user_form.html", {
        "form": form,
        "heading": f"{target.username} hesabını düzenle",
        "submit_label": "Değişiklikleri kaydet",
        "target": target,
        "is_creation": False,
    })


@login_required
@require_POST
def user_change_status(request, pk):
    target = get_object_or_404(User, pk=pk)
    _require_platform_manager(request, target)
    requested = request.POST.get("active")
    if requested not in ("0", "1"):
        return HttpResponseBadRequest("Geçersiz hesap durumu.")
    target = set_account_active(actor=request.user, target=target, active=requested == "1")
    messages.success(request, f"{target.username} hesabının durumu güncellendi.")
    return redirect("accounts:user_detail", pk=target.pk)


def _safe_csv_cell(value):
    """Prevent spreadsheet formula execution when administrators open CSVs."""
    text = str(value if value is not None else "")
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + text
    return text


@login_required
@require_http_methods(["GET"])
def user_export_csv(request):
    _require_roster_viewer(request)
    queryset, _ = _filtered_roster(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="po_tracker_users.csv"'
    response.write("\ufeff")  # UTF-8 BOM for Excel, preserves Turkish characters.
    writer = csv.writer(response)
    writer.writerow(["username", "full_name", "email", "role", "student_number", "department_code", "active"])
    for user in queryset.iterator():
        writer.writerow([
            _safe_csv_cell(user.username), _safe_csv_cell(user.display_name),
            _safe_csv_cell(user.email), _safe_csv_cell(user.role),
            _safe_csv_cell(user.student_number), _safe_csv_cell(user.department_code),
            "1" if user.is_active else "0",
        ])
    return response


@login_required
@require_http_methods(["GET"])
def audit_list(request):
    if not is_platform_admin(request.user):
        raise PermissionDenied("Hesap işlem kayıtlarına erişemezsiniz.")
    entries = AuditLog.objects.select_related("actor", "target")
    action = request.GET.get("action", "")
    if action in AuditLog.Action.values:
        entries = entries.filter(action=action)
    paginator = Paginator(entries, 30)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/audit_list.html", {
        "page_obj": page,
        "actions": AuditLog.Action.choices,
        "selected_action": action,
    })
