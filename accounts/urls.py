from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("switch/", views.switch_user, name="switch_user"),  # prototype only
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
