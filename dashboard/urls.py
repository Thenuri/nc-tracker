from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("register/export.xlsx", views.export_excel, name="export_excel"),
    path("register/export.pdf", views.export_pdf, name="export_pdf"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
