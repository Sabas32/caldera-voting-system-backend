from __future__ import annotations

from rest_framework import serializers

from voting_system.apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "organization",
            "organization_name",
            "actor",
            "actor_email",
            "action",
            "target_type",
            "target_id",
            "metadata",
            "ip_address",
            "correlation_id",
            "created_at",
        )
