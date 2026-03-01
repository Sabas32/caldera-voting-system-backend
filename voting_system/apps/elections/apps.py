from django.apps import AppConfig


class ElectionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "voting_system.apps.elections"
    label = "elections"
