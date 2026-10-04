from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from ncs.models import NC
from ncs.test_workflow import WorkflowTestBase

from . import reminders
from .models import Notification
from .services import notify

S = NC.Status
MONDAY = date(2026, 10, 5)


class ReminderTests(WorkflowTestBase):
    def subjects(self, user):
        return list(Notification.objects.filter(recipient=user).values_list("subject", flat=True))

    def test_validation_due_today_then_missed(self):  # FR-14
        nc = self.new_nc(S.PENDING_VALIDATION, validation_deadline=MONDAY)
        reminders.run_all(MONDAY)
        reminders.run_all(MONDAY)  # second run the same day sends nothing new
        self.assertEqual(self.subjects(self.finance_hod), [f"{nc.nc_id}: please validate today"])

        reminders.run_all(MONDAY + timedelta(days=1))
        self.assertIn(f"{nc.nc_id}: validation deadline missed", self.subjects(self.finance_hod))
        self.assertIn(f"{nc.nc_id}: validation deadline missed", self.subjects(self.manager))

    @override_settings(NC_REMINDER_DAYS_BEFORE_TARGET=7, NC_ESCALATION_DAYS_OVERDUE=14)
    def test_target_date_reminder_overdue_and_escalation(self):  # FR-26, FR-27
        target = MONDAY + timedelta(days=7)
        nc = self.new_nc(S.IN_PROGRESS, target_date=target)

        reminders.target_reminders(MONDAY - timedelta(days=1))  # 8 days before: too early
        self.assertEqual(self.subjects(self.owner), [])
        reminders.target_reminders(MONDAY)  # 7 days before
        self.assertEqual(self.subjects(self.owner), [f"{nc.nc_id}: target date {target:%d %b %Y}"])

        reminders.target_reminders(target + timedelta(days=1))
        self.assertIn(f"{nc.nc_id}: overdue", self.subjects(self.owner))
        self.assertIn(f"{nc.nc_id}: overdue", self.subjects(self.finance_hod))
        self.assertEqual(self.subjects(self.manager), [])  # not yet escalated

        reminders.target_reminders(target + timedelta(days=14))
        self.assertIn(f"{nc.nc_id}: 14 days overdue", self.subjects(self.manager))
        self.assertIn(f"{nc.nc_id}: 14 days overdue", self.subjects(self.delegate))

    def test_catches_up_after_missed_days(self):
        nc = self.new_nc(S.IN_PROGRESS, target_date=MONDAY - timedelta(days=30))
        reminders.target_reminders(MONDAY)  # first run in a long time
        self.assertIn(f"{nc.nc_id}: overdue", self.subjects(self.owner))
        self.assertTrue(any("days overdue" in s for s in self.subjects(self.manager)))

    def test_new_target_date_restarts_reminders(self):  # FR-20 follow-on
        nc = self.new_nc(S.IN_PROGRESS, target_date=MONDAY - timedelta(days=1))
        reminders.target_reminders(MONDAY)
        NC.objects.filter(pk=nc.pk).update(target_date=MONDAY + timedelta(days=10))
        reminders.target_reminders(MONDAY + timedelta(days=12))
        self.assertEqual(self.subjects(self.owner).count(f"{nc.nc_id}: overdue"), 2)

    def test_closed_ncs_get_no_reminders(self):
        self.new_nc(S.CLOSED, target_date=MONDAY - timedelta(days=30))
        self.assertEqual(reminders.target_reminders(MONDAY), 0)

    def test_weekly_digest_on_monday_once(self):  # FR-28
        self.assertEqual(reminders.weekly_digest(MONDAY + timedelta(days=1)), 0)  # Tuesday
        self.assertEqual(reminders.weekly_digest(MONDAY), 2)  # manager + delegate
        self.assertEqual(reminders.weekly_digest(MONDAY), 0)  # already sent this week
        self.assertTrue(any(s.startswith("Weekly NC digest") for s in self.subjects(self.manager)))

    def test_command_runs(self):
        out = StringIO()
        call_command("send_reminders", "--digest", stdout=out)
        self.assertIn("digest notification", out.getvalue())


class NotificationPanelTests(WorkflowTestBase):
    def setUp(self):
        self.mine = notify(self.finance_hod, "For Finance HoD", "Hello", self.nc)
        self.other = notify(self.it_hod, "For IT HoD", "Hello")
        self.client.force_login(self.finance_hod)

    def test_list_shows_only_my_notifications_and_unread_count(self):
        response = self.client.get(reverse("notifications:list"))
        self.assertContains(response, "For Finance HoD")
        self.assertNotContains(response, "For IT HoD")
        self.assertEqual(response.context["nav"]["unread"], 1)

    def test_opening_marks_read_and_goes_to_nc(self):
        response = self.client.post(reverse("notifications:open", args=[self.mine.pk]))
        self.assertRedirects(response, self.nc.get_absolute_url())
        self.mine.refresh_from_db()
        self.assertIsNotNone(self.mine.read_at)

    def test_cannot_open_someone_elses(self):
        response = self.client.post(reverse("notifications:open", args=[self.other.pk]))
        self.assertEqual(response.status_code, 404)

    def test_mark_all_read(self):
        self.client.post(reverse("notifications:read_all"))
        self.assertFalse(self.finance_hod.notifications.filter(read_at__isnull=True).exists())

    def test_email_contains_link_to_nc(self):  # UI-03
        self.assertIn(self.nc.get_absolute_url(), self.mine.message)
