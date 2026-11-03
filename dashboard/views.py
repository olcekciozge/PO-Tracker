from django.shortcuts import redirect, render


def landing(request):
    """Public landing page. Signed-in users go straight to their home page."""
    if request.user.is_authenticated:
        return redirect("accounts:home")
    return render(request, "dashboard/landing.html")