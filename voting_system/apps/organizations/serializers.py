from __future__ import annotations

from rest_framework import serializers

from voting_system.apps.organizations.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    active_elections = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "primary_color_override",
            "logo_url",
            "default_public_results_enabled",
            "default_results_visibility",
            "voter_auto_logout_seconds",
            "default_voter_results_after_vote_enabled",
            "default_voter_results_view_window_seconds",
            "created_at",
            "updated_at",
            "active_elections",
        )
        read_only_fields = ("id", "created_at", "updated_at", "active_elections")
