from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "NC Tracker administration"
admin.site.site_title = "NC Tracker admin"
admin.site.index_title = "Manage lists"  # heading on the admin home page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("ncs/", include("ncs.urls")),
    path("notifications/", include("notifications.urls")),
    path("", include("dashboard.urls")),
    path("", include("core.urls")),
]

# Uploaded files are NOT served from /media/ directly. They are only
# downloadable through ncs views that check the person may see the NC.
