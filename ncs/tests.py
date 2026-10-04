from datetime import date, timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from core.models import Department, Process, Source

from .models import NC, Evidence


class NCModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user("manager", role=User.Role.NC_MANAGER)
        cls.finance = Department.objects.create(name="Finance", code="FIN")
        cls.it = Department.objects.create(name="IT", code="IT")
        cls.process = Process.objects.create(name="Fee collection")
        cls.source = Source.objects.create(name="Daily operations")

    def make_nc(self, **overrides):
        fields = dict(
            raising_department=self.it,
            receiving_department=self.finance,
            process=self.process,
            source=self.source,
            description="Receipt not issued for a fee payment.",
            date_identified=timezone.localdate(),
            identified_by="A. Example",
            logged_by=self.manager,
        )
        fields.update(overrides)
        return NC.objects.create(**fields)

    # --- NC ID (FR-03) --------------------------------------------------------

    def test_nc_ids_are_sequential_within_a_year(self):
        year = timezone.localdate().year
        self.assertEqual(self.make_nc().nc_id, f"NC-{year}-001")
        self.assertEqual(self.make_nc().nc_id, f"NC-{year}-002")

    def test_nc_id_sequence_restarts_each_year(self):
        with mock.patch("ncs.models.timezone.localdate", return_value=date(2026, 12, 31)):
            self.make_nc(date_identified=date(2026, 12, 31))
            self.make_nc(date_identified=date(2026, 12, 31))
        with mock.patch("ncs.models.timezone.localdate", return_value=date(2027, 1, 1)):
            nc = self.make_nc(date_identified=date(2027, 1, 1))
        self.assertEqual(nc.nc_id, "NC-2027-001")

    def test_new_nc_starts_pending_validation(self):
        self.assertEqual(self.make_nc().status, NC.Status.PENDING_VALIDATION)

    # --- No deletion (FR-43) --------------------------------------------------

    def test_single_nc_cannot_be_deleted(self):
        nc = self.make_nc()
        with self.assertRaises(PermissionError):
            nc.delete()
        self.assertTrue(NC.objects.filter(pk=nc.pk).exists())

    def test_bulk_delete_is_blocked(self):
        self.make_nc()
        with self.assertRaises(PermissionError):
            NC.objects.all().delete()
        self.assertEqual(NC.objects.count(), 1)

    # --- Field validation (FR-05) ---------------------------------------------

    def test_date_identified_cannot_be_in_future(self):
        nc = self.make_nc()
        nc.date_identified = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError) as ctx:
            nc.full_clean()
        self.assertIn("date_identified", ctx.exception.message_dict)

    def test_evidence_needs_file_or_link(self):
        evidence = Evidence(nc=self.make_nc(), description="Signed receipt", uploaded_by=self.manager)
        with self.assertRaises(ValidationError):
            evidence.full_clean()
        evidence.link = "https://example.com/receipt"
        evidence.full_clean()  # no error now

    # --- Audit trail (FR-42) --------------------------------------------------

    def test_changes_are_recorded_in_history(self):
        nc = self.make_nc()
        nc.root_cause = "Receipt printer was offline."
        nc.save()
        self.assertEqual(nc.history.count(), 2)  # created + changed
        self.assertEqual(nc.history.first().root_cause, "Receipt printer was offline.")
