"""Tests for the NC screens: who sees what, which actions appear, and that
submitting a form goes through the workflow."""

import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts import permissions as perms

from .models import NC, Evidence
from .queries import my_tasks, visible_ncs
from .test_workflow import WorkflowTestBase

S = NC.Status
TODAY = timezone.localdate

MEDIA_DIR = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_DIR)
class ViewTestBase(WorkflowTestBase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_DIR, ignore_errors=True)
        super().tearDownClass()

    def as_user(self, user):
        self.client.force_login(user)
        return self.client

    def action_url(self, nc, action):
        return reverse("ncs:action", args=[nc.nc_id, action])


class LogNCViewTests(ViewTestBase):
    url = reverse("ncs:log")

    def form_data(self, **overrides):
        data = {
            "raising_department": self.it.pk, "receiving_department": self.finance.pk,
            "process": self.nc.process.pk, "source": self.nc.source.pk,
            "description": "Receipt book missing.", "date_identified": TODAY().isoformat(),
            "identified_by": "A. Person",
        }
        data.update(overrides)
        return data

    def test_only_manager_sees_form(self):
        self.assertEqual(self.as_user(self.manager).get(self.url).status_code, 200)
        self.assertEqual(self.as_user(self.finance_hod).get(self.url).status_code, 403)

    def test_anonymous_is_sent_to_sign_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/?next={self.url}", fetch_redirect_response=False)

    def test_logging_creates_nc_and_opens_it(self):
        response = self.as_user(self.manager).post(self.url, self.form_data())
        nc = NC.objects.latest("pk")
        self.assertRedirects(response, nc.get_absolute_url())
        self.assertEqual(nc.status, S.PENDING_VALIDATION)
        self.assertEqual(nc.logged_by, self.manager)

    def test_errors_are_shown_and_nothing_saved(self):
        before = NC.objects.count()
        future = (TODAY() + timedelta(days=2)).isoformat()
        response = self.as_user(self.manager).post(self.url, self.form_data(date_identified=future,
                                                                           description=""))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be in the future")
        self.assertEqual(NC.objects.count(), before)

    def test_hod_cannot_post(self):
        response = self.as_user(self.finance_hod).post(self.url, self.form_data())
        self.assertEqual(response.status_code, 403)


class DetailViewTests(ViewTestBase):
    def test_visibility(self):
        url = self.nc.get_absolute_url()
        for user, expected in [(self.finance_hod, 200), (self.it_hod, 200), (self.hr_hod, 200),
                               (self.management, 200), (self.it_staff, 200), (self.hr_staff, 403)]:
            with self.subTest(user=user.username):
                self.assertEqual(self.as_user(user).get(url).status_code, expected)

    def test_unknown_nc_is_404(self):
        response = self.as_user(self.manager).get(reverse("ncs:detail", args=["NC-1999-999"]))
        self.assertEqual(response.status_code, 404)

    def test_only_allowed_actions_are_shown(self):
        url = self.nc.get_absolute_url()
        hod_page = self.as_user(self.finance_hod).get(url)
        self.assertContains(hod_page, "Confirm this NC is valid")
        self.assertContains(hod_page, "Dispute it")
        for user in [self.it_hod, self.manager, self.management]:
            with self.subTest(user=user.username):
                page = self.as_user(user).get(url)
                self.assertNotContains(page, "Confirm this NC is valid")
                self.assertContains(page, "Nothing for you to do")

    def test_printable_record(self):
        response = self.as_user(self.management).get(reverse("ncs:print", args=[self.nc.nc_id]))
        self.assertContains(response, f"Non-conformity record: {self.nc.nc_id}")


class ActionViewTests(ViewTestBase):
    def test_validate_button(self):
        response = self.as_user(self.finance_hod).post(self.action_url(self.nc, "validate"))
        self.assertRedirects(response, self.nc.get_absolute_url())
        self.nc.refresh_from_db()
        self.assertEqual(self.nc.status, S.VALID)

    def test_dispute_without_reason_shows_error(self):
        response = self.as_user(self.finance_hod).post(self.action_url(self.nc, "dispute"), {"reason": ""})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "This field is required", status_code=400)
        self.nc.refresh_from_db()
        self.assertEqual(self.nc.status, S.PENDING_VALIDATION)

    def test_dispute_with_reason(self):
        self.as_user(self.finance_hod).post(self.action_url(self.nc, "dispute"), {"reason": "Not ours"})
        self.nc.refresh_from_db()
        self.assertEqual(self.nc.status, S.DISPUTED)

    def test_wrong_person_gets_403(self):
        for user in [self.it_hod, self.manager, self.hr_staff]:
            with self.subTest(user=user.username):
                response = self.as_user(user).post(self.action_url(self.nc, "validate"))
                self.assertEqual(response.status_code, 403)

    def test_wrong_status_redirects_with_message(self):
        response = self.as_user(self.manager).post(self.action_url(self.nc, "verify"),
                                                   {"outcome": "effective"}, follow=True)
        self.assertContains(response, "no longer possible")

    def test_unknown_action_and_get_are_rejected(self):
        client = self.as_user(self.finance_hod)
        self.assertEqual(client.post(self.action_url(self.nc, "delete")).status_code, 404)
        self.assertEqual(client.get(self.action_url(self.nc, "validate")).status_code, 405)

    def test_owner_uploads_evidence_and_only_viewers_can_download(self):
        nc = self.new_nc(S.IN_PROGRESS)
        upload = SimpleUploadedFile("proof.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.as_user(self.owner).post(self.action_url(nc, "add_evidence"),
                                                 {"description": "Signed form", "file": upload})
        self.assertRedirects(response, nc.get_absolute_url())
        evidence = Evidence.objects.get(nc=nc)
        url = reverse("ncs:evidence_download", args=[evidence.pk])

        download = self.as_user(self.it_hod).get(url)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), b"%PDF-1.4 test")
        self.assertEqual(self.as_user(self.hr_staff).get(url).status_code, 403)

    def test_target_date_is_locked_in_action_plan_once_in_progress(self):
        nc = self.new_nc(S.IN_PROGRESS)
        later = (nc.target_date + timedelta(days=30)).isoformat()
        self.as_user(self.owner).post(self.action_url(nc, "save_action_plan"), {
            "root_cause": "New cause", "corrective_action": "ca", "target_date": later})
        nc.refresh_from_db()
        self.assertEqual(nc.root_cause, "New cause")
        self.assertNotEqual(nc.target_date.isoformat(), later)  # disabled field ignored


class HomeAndQueryTests(ViewTestBase):
    def test_home_lists_my_tasks(self):
        page = self.as_user(self.finance_hod).get("/")
        self.assertContains(page, self.nc.nc_id)
        page = self.as_user(self.it_hod).get("/")
        self.assertNotContains(page, self.nc.nc_id)

    def test_tasks_by_role(self):
        disputed = self.new_nc(S.DISPUTED)
        working = self.new_nc(S.IN_PROGRESS)
        self.assertIn(disputed, my_tasks(self.manager))
        self.assertIn(working, my_tasks(self.owner))
        self.assertNotIn(working, my_tasks(self.manager))

    def test_visible_ncs_agrees_with_permission_helper(self):
        self.new_nc(S.CLOSED, raising_department=self.hr, receiving_department=self.hr)
        everyone = [self.manager, self.management, self.finance_hod, self.it_hod, self.hr_hod,
                    self.owner, self.finance_staff, self.it_staff, self.hr_staff]
        for user in everyone:
            with self.subTest(user=user.username):
                expected = {nc.pk for nc in NC.objects.all() if perms.can_view_nc(user, nc)}
                self.assertEqual(set(visible_ncs(user).values_list("pk", flat=True)), expected)


class OverdueFlagTests(ViewTestBase):
    def test_flag_and_query_agree(self):  # FR-25
        past, future = TODAY() - timedelta(days=3), TODAY() + timedelta(days=3)
        cases = [
            (self.new_nc(S.PENDING_VALIDATION, validation_deadline=past), True),
            (self.new_nc(S.PENDING_VALIDATION, validation_deadline=future), False),
            (self.new_nc(S.IN_PROGRESS, target_date=past), True),
            (self.new_nc(S.IN_PROGRESS, target_date=future), False),
            (self.new_nc(S.CLOSED, target_date=past), False),
            (self.new_nc(S.NOT_VALID, validation_deadline=past), False),
        ]
        overdue_ids = set(NC.objects.overdue().values_list("pk", flat=True))
        for nc, expected in cases:
            with self.subTest(nc=nc.nc_id, status=nc.status):
                self.assertEqual(nc.is_overdue, expected)
                self.assertEqual(nc.pk in overdue_ids, expected)

    def test_colours(self):  # UI-04
        self.assertEqual(self.new_nc(S.IN_PROGRESS, target_date=TODAY() - timedelta(days=1)).rag, "red")
        self.assertEqual(self.new_nc(S.IN_PROGRESS, target_date=TODAY() + timedelta(days=5)).rag, "amber")
        self.assertEqual(self.new_nc(S.IN_PROGRESS, target_date=TODAY() + timedelta(days=30)).rag, "green")
        self.assertEqual(self.new_nc(S.CLOSED).rag, "green")
