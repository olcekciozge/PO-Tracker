from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("ogrenci/profil/", views.student_profile, name="student_profile"),
    path("ogretim/derslerim/", views.instructor_course_list, name="instructor_courses"),
]