from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "NC Tracker administration"
admin.site.site_title = "NC Tracker admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
