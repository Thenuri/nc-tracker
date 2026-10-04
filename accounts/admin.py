from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

# Use Django's standard user admin screens for our custom User model.
admin.site.register(User, UserAdmin)
