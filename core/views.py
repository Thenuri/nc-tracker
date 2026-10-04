from django.shortcuts import render


def home(request):
    """Landing page. Will become the user's starting point in later phases."""
    return render(request, "core/home.html")
