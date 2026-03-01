from django.core.management.base import BaseCommand

from voting_system.apps.elections.services import run_scheduled_transitions


class Command(BaseCommand):
    help = "Run election lifecycle transitions (scheduled -> live, live -> closed)."

    def handle(self, *args, **options):
        run_scheduled_transitions()
        self.stdout.write(self.style.SUCCESS("Election transitions executed."))
