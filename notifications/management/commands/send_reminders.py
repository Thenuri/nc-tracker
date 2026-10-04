"""Daily reminders, overdue alerts and escalations.

    python manage.py send_reminders            # normal daily run
    python manage.py send_reminders --digest   # also send the weekly digest now

Schedule it once a day (e.g. 7:00 am) with Windows Task Scheduler or cron.
See README.
"""

from django.core.management.base import BaseCommand

from notifications.reminders import run_all


class Command(BaseCommand):
    help = "Send due reminders, overdue alerts and escalations (run daily)."

    def add_arguments(self, parser):
        parser.add_argument("--digest", action="store_true",
                            help="Send the weekly digest even if today is not Monday.")

    def handle(self, *args, **options):
        sent = run_all(force_digest=options["digest"])
        self.stdout.write(self.style.SUCCESS(
            f"Sent {sent['validation']} validation, {sent['target']} target-date and "
            f"{sent['digest']} digest notification(s)."
        ))
