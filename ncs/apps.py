from django.apps import AppConfig


class NcsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ncs'
    verbose_name = "NC records"  # section heading in the admin
