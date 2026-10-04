from django.shortcuts import render


def home(request):
    """Landing page. Will become the user's starting point in later phases."""
    headed = []
    if request.user.is_authenticated:
        headed = list(request.user.headed_departments.all())
    return render(request, "core/home.html", {"headed_departments": headed})
