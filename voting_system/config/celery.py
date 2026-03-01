import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voting_system.config.settings_dev")

app = Celery("voting_system")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
