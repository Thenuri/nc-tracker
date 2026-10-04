from django.conf import settings


def prototype_mode(request):
    """Expose PROTOTYPE_MODE to every template so base.html can show the banner.

    Templates only ever see this flag; they never read .env themselves.
    """
    return {"PROTOTYPE_MODE": settings.PROTOTYPE_MODE}
