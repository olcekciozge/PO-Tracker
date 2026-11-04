from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("ogrenci/profil/", views.student_profile, name="student_profile"),
]