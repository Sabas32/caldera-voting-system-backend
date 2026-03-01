from django.contrib import admin

from voting_system.apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "organization", "actor", "target_type", "target_id", "created_at")
    list_filter = ("action", "organization")
    search_fields = ("target_id", "actor__email", "organization__name")
