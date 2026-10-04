from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """APIIT staff member using the NC Tracker.

    Empty for now on purpose: Django needs the custom user model in place
    before the first migration. Role and department fields come in Phase 2.
    """
