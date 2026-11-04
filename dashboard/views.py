from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import redirect, render

from outcomes.models import ProgramOutcome

from .selectors import instructor_courses, student_po_profile


def landing(request):
    """Herkese açık ana sayfa. Giriş yapmış kullanıcı kendi sayfasına gider."""
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect("dashboard:student_profile")
        if request.user.is_instructor:
            return redirect("dashboard:instructor_courses")
        return redirect("accounts:home")
    return render(request, "dashboard/landing.html")


# ---------------------------------------------------------------
# Herkese açık tanıtım sayfaları
# ---------------------------------------------------------------
def how_it_works(request):
    return render(request, "public/how_it_works.html")


def roles(request):
    return render(request, "public/roles.html")


def program_outcomes(request):
    outcomes = ProgramOutcome.objects.annotate(
        course_count=Count("lo_links__lo__course", distinct=True)
    )
    return render(request, "public/program_outcomes.html", {"outcomes": outcomes})


def about(request):
    return render(request, "public/about.html")


# ---------------------------------------------------------------
# Öğrenci
# ---------------------------------------------------------------
@login_required
def student_profile(request):
    if not request.user.is_student:
        raise PermissionDenied

    term = request.GET.get("term") or None
    profile = student_po_profile(request.user, term=term)
    pos = profile["pos"]
    with_data = [item for item in pos if item["score"] is not None]
    best = max(with_data, key=lambda item: item["score"]) if with_data else None

    # Seçili PO: adresteki ?po=, yoksa en yüksek skorlu PO
    selected = next((item for item in pos if item["po"].code == request.GET.get("po")), None)
    if selected is None:
        selected = best or (pos[0] if pos else None)

    for item in pos:
        item["selected"] = item is selected
        item["height"] = round(item["score"]) if item["score"] is not None else 0

    formula = ""
    if selected:
        rows = [row for row in selected["breakdown"] if row["score"] is not None]
        if rows:
            parts = " + ".join(f"{row['score']:.1f}".replace(".", ",") + f"×{row['weight']}" for row in rows)
            formula = f"({parts}) ÷ {sum(row['weight'] for row in rows)}"

    return render(request, "student/profile.html", {
        **profile,
        "term": term,
        "best": best,
        "selected": selected,
        "formula": formula,
        "with_data_count": len(with_data),
    })


# ---------------------------------------------------------------
# Öğretim elemanı
# ---------------------------------------------------------------
@login_required
def instructor_course_list(request):
    if not request.user.is_instructor:
        raise PermissionDenied

    cards = instructor_courses(request.user)
    return render(request, "instructor/course_list.html", {
        "cards": cards,
        "student_total": sum(card["course"].student_count for card in cards),
        "incomplete_count": sum(1 for card in cards if not card["setup_ok"]),
    })