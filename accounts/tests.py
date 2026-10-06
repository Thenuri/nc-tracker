from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Department, Process, Source
from ncs.models import NC

from . import permissions as perms
from .models import User


class PermissionTestData(TestCase):
    """One cross-department NC: raised by IT against Finance."""

    @classmethod
    def setUpTestData(cls):
        R = User.Role
        cls.finance = Department.objects.create(name="Finance", code="FIN")
        cls.it = Department.objects.create(name="IT", code="IT")
        cls.hr = Department.objects.create(name="HR", code="HR")

        cls.manager = User.objects.create_user("manager", role=R.NC_MANAGER)
        cls.delegate = User.objects.create_user("delegate", role=R.NC_MANAGER, is_delegate=True)
        cls.management = User.objects.create_user("boss", role=R.MANAGEMENT)
        cls.finance_hod = User.objects.create_user("fin_hod", role=R.HOD, department=cls.finance)
        cls.it_hod = User.objects.create_user("it_hod", role=R.HOD, department=cls.it)
        cls.hr_hod = User.objects.create_user("hr_hod", role=R.HOD, department=cls.hr)
        cls.owner = User.objects.create_user("owner", role=R.ACTION_OWNER, department=cls.finance)
        cls.finance_staff = User.objects.create_user("fin_staff", department=cls.finance)
        cls.it_staff = User.objects.create_user("it_staff", department=cls.it)
        cls.hr_staff = User.objects.create_user("hr_staff", department=cls.hr)
        cls.anonymous = AnonymousUser()

        for dept, hod in [(cls.finance, cls.finance_hod), (cls.it, cls.it_hod), (cls.hr, cls.hr_hod)]:
            dept.hod = hod
            dept.save()

        cls.nc = NC.objects.create(
            raising_department=cls.it,
            receiving_department=cls.finance,
            process=Process.objects.create(name="Fee collection"),
            source=Source.objects.create(name="Daily operations"),
            description="Receipt not issued.",
            date_identified=timezone.localdate(),
            identified_by="Someone",
            logged_by=cls.manager,
            action_owner=cls.owner,
        )

    def assert_only(self, check, allowed):
        """`check(user)` must be True for exactly the users in `allowed`."""
        everyone = [self.manager, self.delegate, self.management, self.finance_hod,
                    self.it_hod, self.hr_hod, self.owner, self.finance_staff,
                    self.it_staff, self.hr_staff, self.anonymous]
        for user in everyone:
            with self.subTest(user=str(user)):
                self.assertEqual(check(user), user in allowed)


class PermissionTests(PermissionTestData):
    def test_only_nc_manager_and_delegate_can_log(self):  # FR-01
        self.assert_only(perms.can_log_nc, [self.manager, self.delegate])

    def test_whole_register_for_manager_management_and_all_hods(self):  # FR-30, FR-31
        self.assert_only(perms.can_view_all_ncs, [
            self.manager, self.delegate, self.management,
            self.finance_hod, self.it_hod, self.hr_hod,
        ])

    def test_who_can_view_this_nc(self):
        # Everyone except an unrelated department's staff and anonymous visitors.
        self.assert_only(lambda u: perms.can_view_nc(u, self.nc), [
            self.manager, self.delegate, self.management,
            self.finance_hod, self.it_hod, self.hr_hod,
            self.owner, self.finance_staff, self.it_staff,  # receiving + raising dept
        ])

    def test_only_receiving_hod_validates(self):  # FR-09, FR-13
        self.assert_only(lambda u: perms.can_validate(u, self.nc), [self.finance_hod])

    def test_only_receiving_hod_assigns_owner(self):  # FR-16
        self.assert_only(lambda u: perms.can_assign_action_owner(u, self.nc), [self.finance_hod])

    def test_action_plan_by_receiving_hod_or_owner_only(self):  # FR-17, FR-40
        # Raising department (IT) and other HoDs can't change it.
        self.assert_only(lambda u: perms.can_edit_action_plan(u, self.nc),
                         [self.finance_hod, self.owner])

    def test_manager_only_actions(self):  # FR-12, FR-21, FR-24
        for check in (perms.can_decide_dispute, perms.can_verify, perms.can_reopen):
            with self.subTest(check=check.__name__):
                self.assert_only(lambda u: check(u, self.nc), [self.manager, self.delegate])

    def test_inactive_user_has_no_rights(self):
        self.manager.is_active = False
        self.assertFalse(perms.can_log_nc(self.manager))


class NomineeTests(PermissionTestData):
    """FR-09: the HoD's nominee acts for the HoD on their department's NCs."""

    def setUp(self):
        self.deputy = User.objects.create_user("fin_deputy", department=self.finance)
        self.finance.nominee = self.deputy
        self.finance.save()
        self.nc = NC.objects.get(pk=self.nc.pk)  # reload with the new nominee

    def test_nominee_has_receiving_hod_rights(self):
        for check in (perms.can_validate, perms.can_assign_action_owner, perms.can_edit_action_plan):
            with self.subTest(check=check.__name__):
                self.assertTrue(check(self.deputy, self.nc))

    def test_nominee_does_not_see_every_department(self):  # FR-30 is for real HoDs
        self.assertFalse(perms.can_view_all_ncs(self.deputy))
        self.assertTrue(perms.can_view_nc(self.deputy, self.nc))  # own department

    def test_nominee_of_another_department_has_no_rights(self):
        self.hr.nominee = self.hr_staff
        self.hr.save()
        self.assertFalse(perms.can_validate(self.hr_staff, self.nc))

    def test_nominee_is_shown_as_hod_nominee_not_staff(self):
        self.assertEqual(self.deputy.role_label, "HoD nominee")
        self.assertEqual(self.finance_staff.role_label, "Staff")
        self.assertEqual(self.finance_hod.role_label, "Head of Department")

    @override_settings(PROTOTYPE_MODE=True)
    def test_switcher_lists_nominee_under_its_own_heading(self):
        self.client.force_login(self.manager)
        html = self.client.get(reverse("core:home")).content.decode()
        self.assertIn('<optgroup label="HoD nominee">', html)

    def test_nominee_must_be_in_department_and_not_the_hod(self):
        from django.core.exceptions import ValidationError
        for person in (self.it_staff, self.finance_hod):
            with self.subTest(person=person.username), self.assertRaises(ValidationError):
                self.finance.nominee = person
                self.finance.full_clean()


class NCManagerAdminAccessTests(TestCase):
    """FR-41: anyone given the NC Manager role can manage the lists in the admin."""

    def test_new_nc_manager_can_manage_lists(self):
        manager = User.objects.create_user("new_manager", role=User.Role.NC_MANAGER)
        manager = User.objects.get(pk=manager.pk)  # fresh copy: permissions aren't cached
        self.assertTrue(manager.is_staff)
        for codename in ("core.change_department", "core.add_process", "core.change_source", "ncs.view_nc"):
            with self.subTest(permission=codename):
                self.assertTrue(manager.has_perm(codename))
        self.assertFalse(manager.has_perm("ncs.change_nc"))  # NCs change via workflow only

    def test_leaving_the_role_removes_list_rights(self):
        user = User.objects.create_user("ex_manager", role=User.Role.NC_MANAGER)
        user.role = User.Role.STAFF
        user.save()
        self.assertFalse(User.objects.get(pk=user.pk).has_perm("core.change_department"))

    def test_other_roles_get_no_admin_access(self):
        hod = User.objects.create_user("plain_hod", role=User.Role.HOD)
        self.assertFalse(hod.is_staff)
        self.assertFalse(hod.has_perm("core.change_department"))


class RoleSwitcherTests(PermissionTestData):
    url = reverse("accounts:switch_user")

    @override_settings(PROTOTYPE_MODE=True)
    def test_switch_logs_in_as_chosen_user(self):
        response = self.client.post(self.url, {"user_id": self.finance_hod.pk, "next": "/"})
        self.assertRedirects(response, "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.finance_hod.pk)

    @override_settings(PROTOTYPE_MODE=True)
    def test_cannot_switch_to_superuser(self):
        admin = User.objects.create_superuser("admin", password="x")
        response = self.client.post(self.url, {"user_id": admin.pk})
        self.assertEqual(response.status_code, 404)

    @override_settings(PROTOTYPE_MODE=True)
    def test_does_not_redirect_to_other_sites(self):
        response = self.client.post(self.url, {"user_id": self.owner.pk, "next": "https://evil.example"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    @override_settings(PROTOTYPE_MODE=False)
    def test_switcher_disabled_outside_prototype(self):
        response = self.client.post(self.url, {"user_id": self.finance_hod.pk})
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(PROTOTYPE_MODE=False)
    def test_switcher_not_shown_outside_prototype(self):
        self.assertNotContains(self.client.get("/"), "Who am I?")
