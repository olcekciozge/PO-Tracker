from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.landing, name="landing"),

    # Herkese açık tanıtım sayfaları
    path("nasil-calisir/", views.how_it_works, name="how_it_works"),
    path("roller/", views.roles, name="roles"),
    path("program-ciktilari/", views.program_outcomes, name="program_outcomes"),
    path("hakkinda/", views.about, name="about"),

    # Giriş gerektiren sayfalar
    path("ogrenci/profil/", views.student_profile, name="student_profile"),
    path("ogretim/derslerim/", views.instructor_course_list, name="instructor_courses"),
]