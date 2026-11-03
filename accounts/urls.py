"""Namespaced routes; include at /accounts/ in the project's root URLconf."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("logout/", views.AccountLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/password/", views.AccountPasswordChangeView.as_view(), name="password_change"),
    path("profile/password/done/", views.AccountPasswordChangeDoneView.as_view(), name="password_change_done"),
    path("password/reset/", views.AccountPasswordResetView.as_view(), name="password_reset"),
    path("password/reset/done/", views.AccountPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", views.AccountPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", views.AccountPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("users/", views.user_list, name="user_list"),
    path("users/export/", views.user_export_csv, name="user_export"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/status/", views.user_change_status, name="user_status"),
    path("audit/", views.audit_list, name="audit_list"),
]
