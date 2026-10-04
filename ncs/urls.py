from django.urls import path

from . import views

app_name = "ncs"

urlpatterns = [
    path("new/", views.log_nc, name="log"),
    path("evidence/<int:pk>/download/", views.download_evidence, name="evidence_download"),
    path("<str:nc_id>/", views.nc_detail, name="detail"),
    path("<str:nc_id>/print/", views.nc_print, name="print"),
    path("<str:nc_id>/attachment/", views.download_attachment, name="attachment"),
    path("<str:nc_id>/do/<str:action>/", views.nc_action, name="action"),
]
