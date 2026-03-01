"""ASGI config for voting_system project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voting_system.config.settings_dev")

application = get_asgi_application()
