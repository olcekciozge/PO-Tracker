"""URL routing while the dashboard app is not yet available."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", RedirectView.as_view(pattern_name="accounts:home", permanent=False)),
]
