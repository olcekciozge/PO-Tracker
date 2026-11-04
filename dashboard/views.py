from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .selectors import student_po_profile


def landing(request):
    """Herkese açık ana sayfa. Giriş yapmış kullanıcı kendi sayfasına gider."""
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect("dashboard:student_profile")
        return redirect("accounts:home")
    return render(request, "dashboard/landing.html")


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