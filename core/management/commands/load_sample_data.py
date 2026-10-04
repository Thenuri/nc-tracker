"""PROTOTYPE: load realistic APIIT-style sample data.

    python manage.py load_sample_data

Creates departments, processes, sources, fake staff (one HoD per department,
Action Owners, NC Manager + delegate, Management) and ~20 NCs in every status,
including overdue and cross-department disputed ones.

Safe to run more than once: lists and users are matched by name, and NCs are
only added if the sample NC Manager hasn't logged any yet. All names are
clearly fake. Dates are relative to today so "overdue" always looks right.
"""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.models import Department, Process, Source
from ncs.dates import add_working_days
from ncs.models import NC, Evidence, ProgressNote, TargetDateChange

DEPARTMENTS = [
    ("Academic", "ACA"),
    ("Admissions", "ADM"),
    ("Finance", "FIN"),
    ("Examinations", "EXM"),
    ("Student Services", "SSV"),
    ("IT", "IT"),
    ("HR", "HR"),
    ("Library", "LIB"),
]

PROCESSES = [
    "Teaching and learning", "Student admissions", "Fee collection",
    "Examinations and assessment", "Student support", "IT services",
    "Staff records", "Library services", "Data protection", "Other",
]

SOURCES = ["Daily operations", "Internal review", "Monitoring / KPI", "Stakeholder feedback", "Other"]

# (username, first name, last name, role, department code, is_delegate)
R = User.Role
USERS = [
    ("nc.manager", "Nadia", "Demo", R.NC_MANAGER, None, False),
    ("nc.delegate", "Ishan", "Example", R.NC_MANAGER, None, True),
    ("management", "Leela", "Sample", R.MANAGEMENT, None, False),
    ("hod.academic", "Anika", "Sample", R.HOD, "ACA", False),
    ("hod.admissions", "Ravi", "Demo", R.HOD, "ADM", False),
    ("hod.finance", "Shalini", "Example", R.HOD, "FIN", False),
    ("hod.exams", "Dinesh", "Test", R.HOD, "EXM", False),
    ("hod.studentservices", "Maya", "Placeholder", R.HOD, "SSV", False),
    ("hod.it", "Kasun", "Mock", R.HOD, "IT", False),
    ("hod.hr", "Tharushi", "Sample", R.HOD, "HR", False),
    ("hod.library", "Nimal", "Fictional", R.HOD, "LIB", False),
    ("owner.academic", "Chamari", "Demo", R.ACTION_OWNER, "ACA", False),
    ("owner.admissions", "Sanduni", "Example", R.ACTION_OWNER, "ADM", False),
    ("owner.finance", "Arjun", "Sample", R.ACTION_OWNER, "FIN", False),
    ("owner.exams", "Ruwan", "Example", R.ACTION_OWNER, "EXM", False),
    ("owner.studentservices", "Dilini", "Test", R.ACTION_OWNER, "SSV", False),
    ("owner.it", "Hasith", "Demo", R.ACTION_OWNER, "IT", False),
]

OWNER_FOR = {
    "ACA": "owner.academic", "ADM": "owner.admissions", "FIN": "owner.finance",
    "EXM": "owner.exams", "SSV": "owner.studentservices", "IT": "owner.it",
}

S = NC.Status
# Each NC: raising dept, receiving dept, process, source, description, who found it,
# days ago it was logged, status, and extra details depending on the status.
# `target` = target date in days from today (negative = already passed).
NCS = [
    # --- Pending validation -------------------------------------------------
    dict(raising="ACA", receiving="EXM", process="Examinations and assessment", source="Daily operations",
         desc="Results for module CS201 were published 3 days after the date in the Academic Calendar.",
         by="Lecturer A. Sample", ago=1, status=S.PENDING_VALIDATION),
    dict(raising="SSV", receiving="ADM", process="Student admissions", source="Stakeholder feedback",
         desc="An offer letter stated the March intake instead of September, contrary to the admissions checklist.",
         by="Advisor B. Demo", ago=8, status=S.PENDING_VALIDATION),  # validation overdue
    dict(raising="LIB", receiving="IT", process="IT services", source="Monitoring / KPI",
         desc="Library catalogue PCs have not had security updates for 60 days; IT policy requires 30.",
         by="Librarian C. Example", ago=10, status=S.PENDING_VALIDATION),  # validation overdue
    dict(raising="HR", receiving="HR", process="Staff records", source="Internal review",
         desc="Two new staff files are missing signed employment contracts.",
         by="HR Officer D. Test", ago=2, status=S.PENDING_VALIDATION),  # same department

    # --- Disputed (cross-department) ----------------------------------------
    dict(raising="FIN", receiving="ACA", process="Examinations and assessment", source="Internal review",
         desc="Resit marks entry sheet was submitted to Finance without HoD sign-off.",
         by="Accountant E. Sample", ago=6, status=S.DISPUTED,
         dispute="Sign-off is not required for resit marks under section 4.2 of the Assessment Regulations."),
    dict(raising="EXM", receiving="LIB", process="Library services", source="Stakeholder feedback",
         desc="The library closed 30 minutes early during exam week without notice to students.",
         by="Exams Officer F. Demo", ago=4, status=S.DISPUTED,
         dispute="Early closure was approved by the Registrar because of a power cut, and a notice was posted."),

    # --- Not valid (dispute upheld) -----------------------------------------
    dict(raising="ADM", receiving="FIN", process="Fee collection", source="Daily operations",
         desc="Refund for a withdrawn applicant was not processed within 14 days.",
         by="Admissions Officer G. Example", ago=20, status=S.NOT_VALID,
         dispute="The applicant had not sent bank details; the 14 days start when details are received.",
         decision="Upheld. Finance procedure FP-07 starts the 14 days on receipt of bank details, "
                  "which arrived 5 days before the refund was paid."),

    # --- Valid, waiting for action plan ---------------------------------------
    dict(raising="IT", receiving="SSV", process="Data protection", source="Monitoring / KPI",
         desc="Student counselling notes are stored in a shared folder that all staff accounts can open.",
         by="IT Analyst H. Mock", ago=12, status=S.VALID,
         dispute="The folder is only used by Student Services staff.",
         decision="Overturned. The access log shows the folder is open to all staff accounts, "
                  "which breaches the data protection policy."),
    dict(raising="ACA", receiving="ACA", process="Teaching and learning", source="Internal review",
         desc="BSc Business Year 2 module handbook does not show the new assessment weighting.",
         by="Programme Leader I. Sample", ago=5, status=S.VALID),

    # --- In progress ------------------------------------------------------------
    dict(raising="FIN", receiving="FIN", process="Fee collection", source="Internal review",
         desc="Daily cash reconciliation was not signed by a second checker on 3 days in September.",
         by="Finance Officer J. Demo", ago=15, status=S.IN_PROGRESS, target=25,
         root_cause="Second checker was on leave and no cover was named.",
         action="Name a back-up checker for each day in the cash procedure and brief the team.",
         notes=["Back-up checker list drafted, waiting for HoD approval."]),
    dict(raising="SSV", receiving="EXM", process="Examinations and assessment", source="Stakeholder feedback",
         desc="An exam timetable clash for 12 students was not resolved before the timetable was published.",
         by="Student Advisor K. Test", ago=18, status=S.IN_PROGRESS, target=4,  # due within 7 days
         root_cause="The clash check was run before late module changes were entered.",
         action="Run the clash report after the module change deadline and before publishing."),
    dict(raising="ACA", receiving="IT", process="IT services", source="Monitoring / KPI",
         desc="The Moodle backup job failed for a week and nobody was alerted.",
         by="Lecturer L. Example", ago=30, status=S.IN_PROGRESS, target=-3,  # overdue
         root_cause="Backup alerts were going to a mailbox nobody checks.",
         action="Send backup alerts to the IT helpdesk queue and test the alert monthly.",
         notes=["Alert rule changed; monthly test not yet scheduled."]),
    dict(raising="HR", receiving="ADM", process="Data protection", source="Daily operations",
         desc="An applicant's personal documents were emailed to an external address by mistake.",
         by="HR Officer M. Sample", ago=50, status=S.IN_PROGRESS, target=-20,  # overdue > 14 days
         root_cause="Email address auto-complete picked the wrong contact.",
         action="Turn off auto-complete for external addresses and train admissions staff.",
         notes=["Training session postponed twice due to intake week."]),
    dict(raising="LIB", receiving="ACA", process="Teaching and learning", source="Daily operations",
         desc="Reading lists for 5 modules refer to out-of-print editions.",
         by="Librarian N. Demo", ago=40, status=S.IN_PROGRESS, target=10,
         root_cause="Reading lists are not reviewed when modules are re-approved.",
         action="Add a reading list check to the module review form and update the 5 lists.",
         date_change=(-5, "Waiting for the publisher to confirm availability of the new editions.")),
    dict(raising="EXM", receiving="SSV", process="Student support", source="Monitoring / KPI",
         desc="Student complaints were not acknowledged within 2 working days as the complaints procedure requires.",
         by="Exams Officer O. Example", ago=45, status=S.IN_PROGRESS, target=14,
         root_cause="No standard acknowledgement template and no daily inbox check.",
         action="Introduce an acknowledgement template and a named person to check the inbox daily.",
         completed=-6, evidence="New acknowledgement template",
         not_effective="The template is in place, but 3 complaints last week were still acknowledged late. "
                       "Please add the daily inbox check and show a week of on-time acknowledgements."),

    # --- Pending verification ---------------------------------------------------
    dict(raising="FIN", receiving="IT", process="IT services", source="Internal review",
         desc="Finance system accounts of 2 staff who left in August are still active.",
         by="Accountant P. Test", ago=25, status=S.PENDING_VERIFICATION, target=5,
         root_cause="HR leaver notices are not sent to IT for finance system accounts.",
         action="Disable the 2 accounts and add finance system access to the leaver checklist.",
         completed=-2, evidence="Screenshot of disabled accounts and updated leaver checklist"),
    dict(raising="ACA", receiving="EXM", process="Examinations and assessment", source="Daily operations",
         desc="Marked answer scripts were stored in an unlocked cabinet in the staff room.",
         by="Lecturer Q. Sample", ago=35, status=S.PENDING_VERIFICATION, target=3,
         root_cause="Lockable cabinet was full, so overflow scripts were kept in an open one.",
         action="Buy a second lockable cabinet and move all scripts.",
         completed=-1, evidence="Photo of new locked cabinet and purchase record"),
    dict(raising="SSV", receiving="FIN", process="Fee collection", source="Stakeholder feedback",
         desc="Two scholarship payments were made without a signed approval form.",
         by="Student Advisor R. Demo", ago=28, status=S.PENDING_VERIFICATION, target=2,
         root_cause="Payment checklist did not include the approval form.",
         action="Add the approval form to the payment checklist and obtain the missing approvals.",
         completed=-3, evidence="Signed approval forms and updated payment checklist"),

    # --- Closed -------------------------------------------------------------------
    dict(raising="ADM", receiving="ADM", process="Student admissions", source="Internal review",
         desc="Walk-in enquiries were not recorded in the enquiry log for two weeks.",
         by="Admissions Officer S. Example", ago=60, status=S.CLOSED, target=-30,
         root_cause="Front desk staff were not aware walk-ins must be logged.",
         action="Brief front desk staff and add a log reminder at the reception desk.",
         completed=-35, closed=-28, evidence="Briefing attendance sheet and enquiry log extract"),
    dict(raising="IT", receiving="FIN", process="Fee collection", source="Daily operations",
         desc="The petty cash box key was kept in an unlocked desk drawer.",
         by="IT Technician T. Mock", ago=75, status=S.CLOSED, target=-55,
         root_cause="No key safe was available in the Finance office.",
         action="Install a key safe and record key handovers.",
         completed=-50, closed=-45, evidence="Photo of key safe and key handover log"),
    dict(raising="EXM", receiving="ACA", process="Examinations and assessment", source="Monitoring / KPI",
         desc="Late submission penalties were applied differently across three modules.",
         by="Exams Officer U. Sample", ago=90, status=S.CLOSED, target=-65,
         root_cause="Module leaders were using an old version of the penalty rules.",
         action="Publish one penalty table on Moodle and remove old copies.",
         completed=-68, closed=-60, evidence="Link to the single penalty table on Moodle"),
]


def at(day, hour=10):
    """A timezone-aware datetime on `day` at `hour`:00."""
    return timezone.make_aware(datetime.combine(day, time(hour, 0)))


class Command(BaseCommand):
    help = "Load realistic sample departments, users and NCs for the prototype."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.PROTOTYPE_MODE:
            self.stderr.write(self.style.ERROR("Refusing to load sample data: PROTOTYPE_MODE is False."))
            return

        departments = self.load_lists()
        users = self.load_users(departments)
        self.load_ncs(departments, users)
        self.stdout.write(self.style.SUCCESS("Sample data ready."))

    # --- Lists ------------------------------------------------------------------

    def load_lists(self):
        departments = {}
        for name, code in DEPARTMENTS:
            # Match by name ignoring case, so entries typed in the admin are reused.
            dept = Department.objects.filter(name__iexact=name).first()
            if dept is None:
                dept = Department.objects.create(name=name, code=code)
            departments[code] = dept
        for name in PROCESSES:
            if not Process.objects.filter(name__iexact=name).exists():
                Process.objects.create(name=name)
        for name in SOURCES:
            if not Source.objects.filter(name__iexact=name).exists():
                Source.objects.create(name=name)
        self.stdout.write(f"Lists: {len(departments)} departments, {Process.objects.count()} processes, "
                          f"{Source.objects.count()} sources.")
        return departments

    # --- Users ------------------------------------------------------------------

    def load_users(self, departments):
        manager_group = self.nc_manager_group()
        users = {}
        for username, first, last, role, dept_code, delegate in USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(
                    first_name=first, last_name=last, role=role, is_delegate=delegate,
                    department=departments.get(dept_code),
                    email=f"{username}@example.com",  # never a real apiit.lk address
                ),
            )
            if created:
                user.set_unusable_password()  # sample users sign in via the switcher only
            if role == R.NC_MANAGER:
                user.is_staff = True  # can open the admin to manage lists (FR-41)
            user.save()
            if role == R.NC_MANAGER:
                user.groups.add(manager_group)
            if role == R.HOD:
                dept = departments[dept_code]
                dept.hod = user
                dept.save()
            users[username] = user
        self.stdout.write(f"Users: {len(users)} sample staff.")
        return users

    def nc_manager_group(self):
        """Admin rights for the NC Manager: edit the lists, view NC records."""
        group, _ = Group.objects.get_or_create(name="NC Manager")
        codenames = [
            f"{action}_{model}"
            for model in ("department", "process", "source")
            for action in ("add", "change", "view")
        ] + ["view_nc", "view_evidence", "view_progressnote", "view_targetdatechange", "view_notification"]
        group.permissions.set(Permission.objects.filter(codename__in=codenames))
        return group

    # --- NCs --------------------------------------------------------------------

    def load_ncs(self, departments, users):
        manager = users["nc.manager"]
        if NC.objects.filter(logged_by=manager).exists():
            self.stdout.write("NCs: sample NCs already loaded, skipping.")
            return

        processes = {p.name.lower(): p for p in Process.objects.all()}
        sources = {s.name.lower(): s for s in Source.objects.all()}
        for spec in NCS:
            self.create_nc(spec, departments, users, processes, sources, manager)
        self.stdout.write(f"NCs: {len(NCS)} sample NCs created.")

    def create_nc(self, spec, departments, users, processes, sources, manager):
        today = timezone.localdate()
        logged = today - timedelta(days=spec["ago"])
        receiving = departments[spec["receiving"]]
        hod = receiving.hod

        nc = NC(
            raising_department=departments[spec["raising"]],
            receiving_department=receiving,
            process=processes[spec["process"].lower()],
            source=sources[spec["source"].lower()],
            description=spec["desc"],
            date_identified=logged - timedelta(days=1),
            identified_by=spec["by"],
            logged_by=manager,
            validation_deadline=add_working_days(logged, settings.NC_VALIDATION_WORKING_DAYS),
        )
        # Sample data recreates PAST states, so it writes the status and the
        # matching fields directly. Real changes always go through ncs/workflow.py.
        nc.status = spec["status"]

        if spec["status"] != S.PENDING_VALIDATION:
            nc.validated_by = hod
            nc.validated_at = at(logged + timedelta(days=1))
        if "dispute" in spec:
            nc.dispute_reason = spec["dispute"]
        if "decision" in spec:
            nc.dispute_decided_by = manager
            nc.dispute_decided_at = at(logged + timedelta(days=3))
            nc.dispute_rationale = spec["decision"]
        if "target" in spec:
            nc.root_cause = spec["root_cause"]
            nc.corrective_action = spec["action"]
            nc.action_owner = users[OWNER_FOR[spec["receiving"]]]
            nc.target_date = today + timedelta(days=spec["target"])
            nc.original_target_date = nc.target_date
        if "date_change" in spec:
            nc.original_target_date = today + timedelta(days=spec["date_change"][0])
        if "completed" in spec:
            nc.completion_date = today + timedelta(days=spec["completed"])
        if "not_effective" in spec:
            nc.verification_outcome = NC.Outcome.NOT_EFFECTIVE
            nc.verification_comments = spec["not_effective"]
            nc.verified_by = manager
            nc.verified_at = at(today - timedelta(days=2))
        if "closed" in spec:
            nc.verification_outcome = NC.Outcome.EFFECTIVE
            nc.verification_comments = "Evidence checked; action is effective."
            nc.verified_by = manager
            nc.verified_at = nc.closed_at = at(today + timedelta(days=spec["closed"]))

        nc._history_user = manager  # history shows the NC Manager as the author
        nc.save()
        # logged_at/created_at are set automatically to "now"; backdate them.
        NC.objects.filter(pk=nc.pk).update(logged_at=at(logged, 9), created_at=at(logged, 9))

        if "date_change" in spec:
            TargetDateChange.objects.create(
                nc=nc, old_date=nc.original_target_date, new_date=nc.target_date,
                reason=spec["date_change"][1], changed_by=hod,
            )
        if "evidence" in spec:
            Evidence.objects.create(
                nc=nc, description=spec["evidence"], uploaded_by=nc.action_owner,
                link=f"https://example.com/evidence/{nc.nc_id}",
            )
        for text in spec.get("notes", []):
            ProgressNote.objects.create(nc=nc, author=nc.action_owner, text=text)
