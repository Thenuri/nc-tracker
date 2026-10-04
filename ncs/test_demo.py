"""Phase 8 demo run-through, as an automated test (SRS acceptance criterion 11).

A cross-department NC is taken from logging to closure through the real
screens, as the sample users in docs/DEMO.md. If this passes, the demo works.
"""

from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Department, Process, Source
from notifications.models import Notification

from .models import NC

S = NC.Status
TODAY = timezone.localdate


@override_settings(PROTOTYPE_MODE=True)
class CrossDepartmentDisputeDemo(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_sample_data", stdout=StringIO())

    def become(self, username):
        """Like choosing a person in "Who am I?"."""
        user = User.objects.get(username=username)
        response = self.client.post(reverse("accounts:switch_user"), {"user_id": user.pk, "next": "/"})
        self.assertEqual(response.status_code, 302)
        return user

    def act(self, action, data=None, expect_status=None):
        response = self.client.post(reverse("ncs:action", args=[self.nc_id, action]), data or {})
        self.assertEqual(response.status_code, 302, f"{action} failed: {response.content[:3000]}")
        nc = NC.objects.get(nc_id=self.nc_id)
        if expect_status:
            self.assertEqual(nc.status, expect_status, action)
        return nc

    def inbox(self, username):
        return Notification.objects.filter(recipient__username=username, nc__nc_id=self.nc_id)

    def test_full_demo(self):
        it = Department.objects.get(code="IT")
        finance = Department.objects.get(code="FIN")

        # 1. NC Manager logs an NC raised by IT against Finance.
        self.become("nc.manager")
        response = self.client.post(reverse("ncs:log"), {
            "raising_department": it.pk, "receiving_department": finance.pk,
            "process": Process.objects.get(name="Fee collection").pk,
            "source": Source.objects.get(name__iexact="Daily operations").pk,
            "description": "Online fee payments are not reconciled with the bank statement each week.",
            "date_identified": TODAY().isoformat(), "identified_by": "IT Analyst Z. Sample",
        })
        nc = NC.objects.latest("pk")
        self.nc_id = nc.nc_id
        self.assertRedirects(response, nc.get_absolute_url())
        self.assertEqual(nc.status, S.PENDING_VALIDATION)
        self.assertTrue(self.inbox("hod.finance").exists())   # FR-08
        self.assertTrue(self.inbox("hod.it").exists())        # FR-07
        self.assertTrue(any(nc.get_absolute_url() in m.body for m in mail.outbox))  # UI-03

        # 2. Every HoD can see it (FR-30), but the raising HoD cannot validate (FR-13).
        self.become("hod.it")
        page = self.client.get(nc.get_absolute_url())
        self.assertContains(page, "Nothing for you to do")

        # 3. Finance HoD disputes it.
        self.become("hod.finance")
        self.assertContains(self.client.get("/"), self.nc_id)  # in "Waiting for you"
        self.act("dispute", {"reason": "Reconciliation is IT's automated job, not Finance's."},
                 expect_status=S.DISPUTED)
        self.assertTrue(self.inbox("nc.manager").filter(subject__contains="disputed").exists())  # FR-11

        # 4. NC Manager overturns the dispute with a rationale.
        self.become("nc.manager")
        self.assertContains(self.client.get("/"), self.nc_id)
        self.act("decide_dispute", {"decision": "overturn",
                                    "rationale": "Procedure FP-03 makes Finance responsible for reconciliation."},
                 expect_status=S.VALID)

        # 5. Finance HoD assigns the Action Owner.
        self.become("hod.finance")
        owner = User.objects.get(username="owner.finance")
        self.act("assign_action_owner", {"action_owner": owner.pk})
        self.assertTrue(self.inbox("owner.finance").filter(subject__contains="Action Owner").exists())  # FR-16

        # 6. Action Owner records the plan (4 fields, NFR-02).
        self.become("owner.finance")
        target = TODAY() + timedelta(days=21)
        self.act("save_action_plan", {"root_cause": "No one was named to do the weekly check.",
                                      "corrective_action": "Name a reconciler and add a weekly checklist.",
                                      "target_date": target.isoformat()},
                 expect_status=S.IN_PROGRESS)

        # 7. Sending for verification without evidence is refused (FR-19).
        response = self.client.post(reverse("ncs:action", args=[self.nc_id, "submit_for_verification"]),
                                    {"completion_date": TODAY().isoformat()})
        self.assertContains(response, "add evidence", status_code=400)

        # 8. Evidence, then send for verification.
        self.act("add_evidence", {"description": "Signed weekly checklist",
                                  "link": "https://example.com/checklist"})
        self.act("submit_for_verification", {"completion_date": TODAY().isoformat()},
                 expect_status=S.PENDING_VERIFICATION)

        # 9. NC Manager: not effective – back to the owner with comments (FR-23).
        self.become("nc.manager")
        self.act("verify", {"outcome": "not_effective",
                            "comments": "Only one week shown. Please show four weeks."},
                 expect_status=S.IN_PROGRESS)
        self.become("owner.finance")
        self.assertContains(self.client.get(nc.get_absolute_url()), "Please show four weeks.")

        # 10. Owner adds a note and more evidence, sends again.
        self.act("add_progress_note", {"text": "Four weeks of checklists now attached."})
        self.act("add_evidence", {"description": "Checklists weeks 1–4", "link": "https://example.com/4w"})
        self.act("submit_for_verification", {"completion_date": TODAY().isoformat()},
                 expect_status=S.PENDING_VERIFICATION)

        # 11. NC Manager verifies effective: closed and locked (FR-21, FR-24).
        self.become("nc.manager")
        nc = self.act("verify", {"outcome": "effective", "comments": "Four weeks done."},
                      expect_status=S.CLOSED)
        self.assertIsNotNone(nc.closed_at)
        self.become("owner.finance")
        self.assertContains(self.client.get(nc.get_absolute_url()), "Nothing for you to do")

        # 12. The audit trail and reports show the whole story.
        reasons = list(nc.history.order_by("history_date").values_list("history_change_reason", flat=True))
        self.assertEqual(reasons[0], "Logged")
        self.assertEqual(reasons[-1], "Verified effective and closed")
        self.assertIn("Dispute overturned", reasons)
        self.assertIn("Verified not effective – returned for rework", reasons)

        self.become("management")
        record = self.client.get(reverse("ncs:print", args=[self.nc_id]))
        for text in ["Part A", "Overturned (valid)", "Name a reconciler", "Checklists weeks 1–4", "Effective"]:
            self.assertContains(record, text)
        register = self.client.get(reverse("dashboard:register"), {"status": "CLOSED", "q": self.nc_id})
        self.assertEqual(register.context["total"], 1)
