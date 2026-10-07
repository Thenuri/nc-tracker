"""Tests for ncs/workflow.py: every allowed and blocked transition, required
fields, permissions and notifications."""

from datetime import date, timedelta

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.utils import timezone

from accounts.models import User
from accounts.tests import PermissionTestData
from notifications.models import Notification

from . import workflow as wf
from .dates import add_working_days
from .models import NC, Evidence, TargetDateChange

S = NC.Status
TODAY = timezone.localdate


class WorkflowTestBase(PermissionTestData):
    """Cross-department set-up from accounts tests: IT raises, Finance receives."""

    def new_nc(self, status=S.PENDING_VALIDATION, **fields):
        """An NC already sitting in `status` (test set-up only, skips the workflow)."""
        defaults = dict(
            raising_department=self.it, receiving_department=self.finance,
            process=self.nc.process, source=self.nc.source,
            description="Receipt not issued.", date_identified=TODAY(),
            identified_by="Someone", logged_by=self.manager,
        )
        if status in (S.IN_PROGRESS, S.PENDING_VERIFICATION, S.CLOSED):
            defaults.update(root_cause="rc", corrective_action="ca", action_owner=self.owner,
                            target_date=TODAY() + timedelta(days=10))
        defaults.update(fields)
        nc = NC.objects.create(**defaults)
        NC.objects.filter(pk=nc.pk).update(status=status)
        nc.refresh_from_db()
        return nc

    def notified(self, user):
        return Notification.objects.filter(recipient=user)


# --- The transition table itself ----------------------------------------------------

class TransitionTableTests(WorkflowTestBase):
    def test_allowed_transitions_match_the_srs(self):
        """Exactly the 10 transitions in CLAUDE.md / SRS Section 3, nothing more."""
        expected = {
            (S.PENDING_VALIDATION, S.VALID), (S.PENDING_VALIDATION, S.DISPUTED),
            (S.DISPUTED, S.VALID), (S.DISPUTED, S.NOT_VALID),
            (S.VALID, S.IN_PROGRESS), (S.IN_PROGRESS, S.PENDING_VERIFICATION),
            (S.PENDING_VERIFICATION, S.CLOSED), (S.PENDING_VERIFICATION, S.IN_PROGRESS),
            (S.CLOSED, S.IN_PROGRESS),
        }
        actual = {(f, t) for f, targets in wf.ALLOWED_TRANSITIONS.items() for t in targets}
        self.assertEqual(actual, expected)
        self.assertEqual(set(wf.ALLOWED_TRANSITIONS), set(S.values))  # every status listed

    def test_move_blocks_unlisted_transitions(self):
        for from_status in S.values:
            for to_status in S.values:
                if to_status in wf.ALLOWED_TRANSITIONS[from_status]:
                    continue
                with self.subTest(frm=from_status, to=to_status):
                    nc = self.new_nc(from_status)
                    with self.assertRaises(wf.WorkflowError):
                        wf._move(nc, to_status)


# --- Every action in every status ----------------------------------------------------

class ActionStatusMatrixTests(WorkflowTestBase):
    """Each action, called by a permitted person with valid input, must work
    only in its allowed statuses and be blocked (status unchanged) in all others."""

    def call(self, action, nc):
        hod, mgr, soon = self.finance_hod, self.manager, TODAY() + timedelta(days=10)
        calls = {
            "validate": lambda: wf.validate(nc, hod),
            "dispute": lambda: wf.dispute(nc, hod, "Not our process."),
            "decide_dispute": lambda: wf.decide_dispute(nc, mgr, True, "Agreed."),
            "assign_action_owner": lambda: wf.assign_action_owner(nc, hod, self.owner),
            "save_action_plan": lambda: wf.save_action_plan(
                nc, hod, "rc", "ca", nc.target_date or soon, action_owner=self.owner),
            "change_target_date": lambda: wf.change_target_date(nc, hod, soon + timedelta(days=5), "Delay"),
            "add_progress_note": lambda: wf.add_progress_note(nc, hod, "Update"),
            "add_evidence": lambda: wf.add_evidence(nc, hod, "Photo", link="https://example.com/e"),
            "submit_for_verification": lambda: wf.submit_for_verification(nc, hod, TODAY()),
            "verify": lambda: wf.verify(nc, mgr, True),
            "reopen": lambda: wf.reopen(nc, mgr, "Problem came back."),
        }
        return calls[action]()

    def test_every_action_in_every_status(self):
        for action, (allowed_statuses, _) in wf.ACTIONS.items():
            for status in S.values:
                with self.subTest(action=action, status=status):
                    nc = self.new_nc(status)
                    if action == "submit_for_verification":
                        Evidence.objects.create(nc=nc, description="x", link="https://e.x",
                                                uploaded_by=self.owner)
                    if status in allowed_statuses:
                        self.call(action, nc)  # must not raise
                    else:
                        with self.assertRaises(wf.WorkflowError):
                            self.call(action, nc)
                        nc.refresh_from_db()
                        self.assertEqual(nc.status, status)

    def test_closed_and_not_valid_are_locked(self):
        mgr_and_hod = [self.manager, self.finance_hod, self.owner]
        for status, still_allowed in [(S.CLOSED, {"reopen"}), (S.NOT_VALID, set())]:
            nc = self.new_nc(status)
            allowed = set().union(*(wf.available_actions(nc, u) for u in mgr_and_hod))
            self.assertEqual(allowed, still_allowed)


# --- Logging ------------------------------------------------------------------------------

class LogNCTests(WorkflowTestBase):
    def unsaved_nc(self, **fields):
        defaults = dict(
            raising_department=self.it, receiving_department=self.finance,
            process=self.nc.process, source=self.nc.source, description="Receipt not issued.",
            date_identified=TODAY(), identified_by="Someone",
        )
        defaults.update(fields)
        return NC(**defaults)

    def test_manager_logs_nc(self):
        nc = wf.log_nc(self.manager, self.unsaved_nc())
        self.assertEqual(nc.status, S.PENDING_VALIDATION)
        self.assertEqual(nc.logged_by, self.manager)
        self.assertEqual(nc.validation_deadline, add_working_days(TODAY(), 3))
        self.assertTrue(nc.nc_id.startswith(f"NC-{TODAY().year}-"))
        self.assertEqual(nc.history.first().history_change_reason, "Logged")

    def test_logging_notifies_receiving_and_raising_hods(self):  # FR-07, FR-08
        nc = wf.log_nc(self.manager, self.unsaved_nc())
        self.assertTrue(self.notified(self.finance_hod).filter(nc=nc).exists())
        self.assertTrue(self.notified(self.it_hod).filter(nc=nc).exists())

    def test_delegate_can_log(self):  # NFR-08
        self.assertEqual(wf.log_nc(self.delegate, self.unsaved_nc()).logged_by, self.delegate)

    def test_others_cannot_log(self):  # FR-01
        for user in [self.finance_hod, self.owner, self.management, self.it_staff]:
            with self.subTest(user=user.username), self.assertRaises(PermissionDenied):
                wf.log_nc(user, self.unsaved_nc())
        self.assertEqual(NC.objects.count(), 1)  # only the fixture NC

    def test_required_fields_and_future_date(self):  # FR-05
        with self.assertRaises(wf.WorkflowError):
            wf.log_nc(self.manager, self.unsaved_nc(description=""))
        with self.assertRaises(wf.WorkflowError):
            wf.log_nc(self.manager, self.unsaved_nc(date_identified=TODAY() + timedelta(days=1)))

    def test_other_process_needs_description(self):
        other = type(self.nc.process).objects.create(name="Other")
        with self.assertRaises(wf.WorkflowError):
            wf.log_nc(self.manager, self.unsaved_nc(process=other))
        wf.log_nc(self.manager, self.unsaved_nc(process=other, process_other="Car park"))

    def test_same_department_still_needs_validation_by_default(self):
        nc = wf.log_nc(self.manager, self.unsaved_nc(raising_department=self.finance))
        self.assertEqual(nc.status, S.PENDING_VALIDATION)

    @override_settings(NC_SAME_DEPARTMENT_NEEDS_VALIDATION=False)
    def test_same_department_can_skip_validation_if_configured(self):
        nc = wf.log_nc(self.manager, self.unsaved_nc(raising_department=self.finance))
        self.assertEqual(nc.status, S.VALID)
        cross = wf.log_nc(self.manager, self.unsaved_nc())
        self.assertEqual(cross.status, S.PENDING_VALIDATION)  # cross-dept unaffected


# --- Validation and disputes ---------------------------------------------------------

class ValidationTests(WorkflowTestBase):
    def test_validate(self):
        nc = wf.validate(self.new_nc(), self.finance_hod)
        self.assertEqual(nc.status, S.VALID)
        self.assertEqual(nc.validated_by, self.finance_hod)

    def test_raising_hod_cannot_validate(self):  # FR-13
        with self.assertRaises(PermissionDenied):
            wf.validate(self.new_nc(), self.it_hod)

    def test_dispute_needs_reason_and_alerts_managers(self):  # FR-10, FR-11
        nc = self.new_nc()
        with self.assertRaises(wf.WorkflowError):
            wf.dispute(nc, self.finance_hod, "   ")
        wf.dispute(nc, self.finance_hod, "Not a Finance process.")
        self.assertEqual(nc.status, S.DISPUTED)
        self.assertTrue(self.notified(self.manager).filter(nc=nc).exists())
        self.assertTrue(self.notified(self.delegate).filter(nc=nc).exists())

    def test_uphold_dispute_makes_not_valid(self):  # FR-12, FR-15
        nc = wf.decide_dispute(self.new_nc(S.DISPUTED), self.manager, True, "Correct, out of scope.")
        self.assertEqual(nc.status, S.NOT_VALID)
        self.assertEqual(nc.dispute_rationale, "Correct, out of scope.")
        self.assertTrue(NC.objects.filter(pk=nc.pk).exists())  # kept in register

    def test_overturn_dispute_makes_valid(self):
        nc = wf.decide_dispute(self.new_nc(S.DISPUTED), self.manager, False, "Evidence shows a breach.")
        self.assertEqual(nc.status, S.VALID)
        self.assertTrue(self.notified(self.finance_hod).filter(nc=nc).exists())

    def test_decision_needs_rationale_and_manager(self):
        nc = self.new_nc(S.DISPUTED)
        with self.assertRaises(wf.WorkflowError):
            wf.decide_dispute(nc, self.manager, True, "")
        with self.assertRaises(PermissionDenied):
            wf.decide_dispute(nc, self.finance_hod, True, "I agree with myself.")


# --- Action planning -----------------------------------------------------------------

class ActionPlanTests(WorkflowTestBase):
    def test_assign_owner_notifies_them(self):  # FR-16
        nc = wf.assign_action_owner(self.new_nc(S.VALID), self.finance_hod, self.owner)
        self.assertEqual(nc.action_owner, self.owner)
        self.assertTrue(self.notified(self.owner).filter(nc=nc).exists())

    def test_owner_must_be_in_receiving_department(self):
        with self.assertRaises(wf.WorkflowError):
            wf.assign_action_owner(self.new_nc(S.VALID), self.finance_hod, self.it_staff)

    def test_complete_plan_moves_to_in_progress(self):  # FR-17
        target = TODAY() + timedelta(days=30)
        nc = wf.save_action_plan(self.new_nc(S.VALID), self.finance_hod, "rc", "ca", target,
                                 action_owner=self.owner)
        self.assertEqual(nc.status, S.IN_PROGRESS)
        self.assertEqual(nc.original_target_date, target)

    def test_plan_needs_all_four_fields(self):
        target = TODAY() + timedelta(days=30)
        nc = self.new_nc(S.VALID)
        for kwargs in [
            dict(root_cause="", corrective_action="ca", target_date=target, action_owner=self.owner),
            dict(root_cause="rc", corrective_action="", target_date=target, action_owner=self.owner),
            dict(root_cause="rc", corrective_action="ca", target_date=None, action_owner=self.owner),
            dict(root_cause="rc", corrective_action="ca", target_date=target),  # no owner
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(wf.WorkflowError):
                wf.save_action_plan(nc, self.finance_hod, **kwargs)
        nc.refresh_from_db()
        self.assertEqual(nc.status, S.VALID)

    def test_owner_can_update_plan_but_not_target_date(self):
        nc = self.new_nc(S.IN_PROGRESS)
        wf.save_action_plan(nc, self.owner, "Better root cause", "ca", nc.target_date)
        self.assertEqual(nc.root_cause, "Better root cause")
        with self.assertRaises(wf.WorkflowError):
            wf.save_action_plan(nc, self.owner, "rc", "ca", nc.target_date + timedelta(days=1))

    def test_raising_department_cannot_edit_plan(self):  # FR-40
        for user in [self.it_hod, self.it_staff, self.hr_hod]:
            with self.subTest(user=user.username), self.assertRaises(PermissionDenied):
                wf.save_action_plan(self.new_nc(S.VALID), user, "rc", "ca", TODAY())

    def test_change_target_date_keeps_original(self):  # FR-20
        nc = self.new_nc(S.IN_PROGRESS)
        nc.original_target_date = original = nc.target_date
        nc.save()
        with self.assertRaises(wf.WorkflowError):
            wf.change_target_date(nc, self.owner, original + timedelta(days=7), "")
        wf.change_target_date(nc, self.owner, original + timedelta(days=7), "Supplier delay")
        self.assertEqual(nc.original_target_date, original)
        change = TargetDateChange.objects.get(nc=nc)
        self.assertEqual((change.old_date, change.reason), (original, "Supplier delay"))


# --- Completion, verification, closure ---------------------------------------------

class CompletionTests(WorkflowTestBase):
    def add_evidence(self, nc):
        wf.add_evidence(nc, self.owner, "Signed checklist", link="https://example.com/e")

    def test_evidence_needs_file_or_link(self):
        with self.assertRaises(wf.WorkflowError):
            wf.add_evidence(self.new_nc(S.IN_PROGRESS), self.owner, "Nothing attached")

    def test_submit_needs_evidence_and_completion_date(self):  # FR-19
        nc = self.new_nc(S.IN_PROGRESS)
        with self.assertRaises(wf.WorkflowError):
            wf.submit_for_verification(nc, self.owner, TODAY())  # no evidence
        self.add_evidence(nc)
        with self.assertRaises(wf.WorkflowError):
            wf.submit_for_verification(nc, self.owner, None)
        with self.assertRaises(wf.WorkflowError):
            wf.submit_for_verification(nc, self.owner, TODAY() + timedelta(days=1))
        wf.submit_for_verification(nc, self.owner, TODAY())
        self.assertEqual(nc.status, S.PENDING_VERIFICATION)
        self.assertTrue(self.notified(self.manager).filter(nc=nc).exists())

    def test_effective_closes(self):  # FR-21, FR-22
        nc = wf.verify(self.new_nc(S.PENDING_VERIFICATION), self.manager, True)
        self.assertEqual(nc.status, S.CLOSED)
        self.assertIsNotNone(nc.closed_at)
        self.assertEqual(nc.verification_outcome, NC.Outcome.EFFECTIVE)

    def test_not_effective_needs_comments_and_returns_to_owner(self):  # FR-23
        nc = self.new_nc(S.PENDING_VERIFICATION)
        with self.assertRaises(wf.WorkflowError):
            wf.verify(nc, self.manager, False, "")
        wf.verify(nc, self.manager, False, "Still happening.")
        self.assertEqual(nc.status, S.IN_PROGRESS)
        note = self.notified(self.owner).get(nc=nc)
        self.assertIn("Still happening.", note.message)

    def test_only_manager_verifies(self):
        for user in [self.finance_hod, self.owner, self.management]:
            with self.subTest(user=user.username), self.assertRaises(PermissionDenied):
                wf.verify(self.new_nc(S.PENDING_VERIFICATION), user, True)

    def test_reopen_clears_old_verification(self):
        nc = self.new_nc(S.PENDING_VERIFICATION, completion_date=TODAY())
        Evidence.objects.create(nc=nc, description="Receipt", link="https://example.com", uploaded_by=self.owner)
        wf.verify(nc, self.manager, True)
        wf.reopen(nc, self.manager, "Same problem found again.")
        nc.refresh_from_db()
        self.assertEqual(nc.verification_outcome, "")
        self.assertIsNone(nc.verified_by)
        self.assertIsNone(nc.completion_date)
        # The earlier "Effective" result is still in the audit trail (FR-42).
        self.assertIn(NC.Outcome.EFFECTIVE, nc.history.values_list("verification_outcome", flat=True))

    def test_reopen_needs_reason_and_is_in_history(self):  # FR-24
        nc = self.new_nc(S.CLOSED)
        with self.assertRaises(wf.WorkflowError):
            wf.reopen(nc, self.manager, "")
        with self.assertRaises(PermissionDenied):
            wf.reopen(nc, self.finance_hod, "Want to change it")
        wf.reopen(nc, self.manager, "Same problem found again.")
        self.assertEqual(nc.status, S.IN_PROGRESS)
        self.assertIsNone(nc.closed_at)
        latest = nc.history.first()
        self.assertEqual(latest.history_user, self.manager)
        self.assertEqual(latest.history_change_reason, "Reopened: Same problem found again.")


# --- What each person sees as available --------------------------------------------

class AvailableActionsTests(WorkflowTestBase):
    def test_pending_validation(self):
        nc = self.new_nc()
        self.assertEqual(wf.available_actions(nc, self.finance_hod), {"validate", "dispute"})
        for user in [self.manager, self.it_hod, self.owner, self.management]:
            with self.subTest(user=user.username):
                self.assertEqual(wf.available_actions(nc, user), set())

    def test_in_progress(self):
        nc = self.new_nc(S.IN_PROGRESS)
        owner_actions = {"save_action_plan", "change_target_date", "add_progress_note",
                         "add_evidence", "submit_for_verification"}
        self.assertEqual(wf.available_actions(nc, self.owner), owner_actions)
        self.assertEqual(wf.available_actions(nc, self.finance_hod), owner_actions | {"assign_action_owner"})
        self.assertEqual(wf.available_actions(nc, self.manager), set())


# --- notify() and dates -------------------------------------------------------------------

class NotifyTests(WorkflowTestBase):
    def test_notify_saves_and_emails(self):
        from notifications.services import notify
        self.finance_hod.email = "fin.hod@example.com"
        self.finance_hod.save()
        notification = notify(self.finance_hod, "Hello", "Body", self.nc)
        self.assertEqual(notification.recipient, self.finance_hod)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["fin.hod@example.com"])

    def test_nominee_is_told_about_new_ncs(self):  # FR-08, FR-09
        deputy = User.objects.create_user("fin_deputy", department=self.finance)
        self.finance.nominee = deputy
        self.finance.save()
        nc = wf.log_nc(self.manager, NC(
            raising_department=self.it, receiving_department=self.finance,
            process=self.nc.process, source=self.nc.source, description="Late refund.",
            date_identified=TODAY(), identified_by="Someone",
        ))
        self.assertTrue(self.notified(deputy).filter(subject__contains="new NC").exists())
        self.assertTrue(self.notified(self.finance_hod).filter(subject__contains="new NC").exists())

    def test_notify_without_recipient_does_nothing(self):
        from notifications.services import notify
        self.assertIsNone(notify(None, "Hello", "Body"))


class WorkingDaysTests(PermissionTestData):
    def test_skips_weekends(self):
        friday = date(2026, 10, 2)
        self.assertEqual(add_working_days(friday, 3), date(2026, 10, 7))  # Wednesday
        self.assertEqual(add_working_days(friday, 1), date(2026, 10, 5))  # Monday

    def test_skips_public_holidays(self):  # FR-14
        from core.models import PublicHoliday
        friday = date(2026, 10, 2)
        PublicHoliday.objects.create(date=date(2026, 10, 5), name="Test holiday")  # the Monday
        self.assertEqual(add_working_days(friday, 1), date(2026, 10, 6))  # Tuesday instead
        self.assertEqual(add_working_days(friday, 3), date(2026, 10, 8))  # Thursday instead of Wednesday

    def test_logging_uses_holidays(self):
        from core.models import PublicHoliday
        tomorrow = TODAY() + timedelta(days=1)
        PublicHoliday.objects.create(date=tomorrow, name="Test holiday")
        nc = wf.log_nc(self.manager, NC(
            raising_department=self.it, receiving_department=self.finance, process=self.nc.process,
            source=self.nc.source, description="x", date_identified=TODAY(), identified_by="y",
        ))
        self.assertEqual(nc.validation_deadline, add_working_days(TODAY(), 3, holidays={tomorrow}))
