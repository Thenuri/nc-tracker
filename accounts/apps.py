from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = "People"  # section heading in the admin

    def ready(self):
        from .admin_access import ensure_nc_manager_group

        # Every `migrate` makes sure the NC Manager group exists with the
        # right permissions (FR-41), on any server, without sample data.
        post_migrate.connect(ensure_nc_manager_group, dispatch_uid="accounts.nc_manager_group")
