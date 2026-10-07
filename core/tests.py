from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.tests import PermissionTestData
from ncs.models import NC

from .models import Department

BANNER_TEXT = "PROTOTYPE – sample data"


class HomePageTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")

    @override_settings(PROTOTYPE_MODE=True)
    def test_banner_shown_in_prototype_mode(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, BANNER_TEXT)

    @override_settings(PROTOTYPE_MODE=False)
    def test_banner_hidden_outside_prototype_mode(self):
        # Real users must never see the prototype banner in production.
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, BANNER_TEXT)


@override_settings(PROTOTYPE_MODE=True)
class SampleDataTests(TestCase):
    def load(self):
        call_command("load_sample_data", stdout=StringIO())

    def test_creates_departments_with_hods_and_ncs_in_every_status(self):
        self.load()
        self.assertEqual(Department.objects.count(), 8)
        self.assertFalse(Department.objects.filter(hod__isnull=True).exists())
        self.assertGreaterEqual(NC.objects.count(), 20)
        statuses = set(NC.objects.values_list("status", flat=True))
        self.assertEqual(statuses, set(NC.Status.values))

    def test_includes_cross_department_disputes(self):
        self.load()
        disputed = NC.objects.filter(status=NC.Status.DISPUTED)
        self.assertTrue(any(nc.raising_department_id != nc.receiving_department_id for nc in disputed))

    def test_running_twice_does_not_duplicate(self):
        self.load()
        counts = (NC.objects.count(), User.objects.count())
        self.load()
        self.assertEqual((NC.objects.count(), User.objects.count()), counts)

    @override_settings(PROTOTYPE_MODE=False)
    def test_refuses_outside_prototype_mode(self):
        call_command("load_sample_data", stdout=StringIO(), stderr=StringIO())
        self.assertEqual(NC.objects.count(), 0)


class ListAdminTests(PermissionTestData):
    """The admin screens the NC Manager uses for the lists (FR-41)."""

    def setUp(self):
        self.client.force_login(self.manager)

    def test_list_pages_load_with_counts(self):
        for name in ("department", "process", "source"):
            with self.subTest(list=name):
                response = self.client.get(reverse(f"admin:core_{name}_changelist"))
                self.assertEqual(response.status_code, 200)
        page = self.client.get(reverse("admin:core_department_changelist"))
        finance = next(d for d in page.context["cl"].result_list if d.code == "FIN")
        self.assertEqual((finance.received, finance.open), (1, 1))

    def test_admin_home_shows_a_card_per_list(self):
        page = self.client.get(reverse("admin:index"))
        self.assertContains(page, "admin-card", count=None)
        self.assertContains(page, "APIIT departments, their Head of Department and HoD nominee.")
        self.assertContains(page, reverse("admin:core_department_add"))

    def test_list_page_title_is_plain(self):
        page = self.client.get(reverse("admin:core_department_changelist"))
        self.assertEqual(page.context["title"], "Departments")

    def test_lists_can_never_be_deleted(self):
        self.client.force_login(User.objects.create_superuser("root", password="x"))
        url = reverse("admin:core_department_delete", args=[self.finance.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_nominee_choices_are_only_department_members(self):
        page = self.client.get(reverse("admin:core_department_change", args=[self.finance.pk]))
        choices = set(page.context["adminform"].form.fields["nominee"].queryset)
        self.assertEqual(choices, {self.finance_hod, self.owner, self.finance_staff})


class HelpPageTests(TestCase):
    """UI-06: the one-page guide."""

    def test_open_to_everyone(self):
        response = self.client.get(reverse("core:help"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Found a problem? Tell the NC Manager")
        self.assertContains(response, "For Heads of Department and nominees")
        self.assertContains(response, "For Action Owners")

    @override_settings(NC_VALIDATION_WORKING_DAYS=5, NC_REMINDER_DAYS_BEFORE_TARGET=10)
    def test_numbers_follow_the_settings(self):
        response = self.client.get(reverse("core:help"))
        self.assertContains(response, "Within 5 working days")
        self.assertContains(response, "10 days before the target date")

    def test_lists_the_nc_managers(self):
        User.objects.create_user("mgr", first_name="Test", last_name="Manager", role=User.Role.NC_MANAGER)
        self.assertContains(self.client.get(reverse("core:help")), "Test Manager")

