from __future__ import annotations

from rest_framework import serializers

from voting_system.apps.elections.models import Candidate, Election, Post


class ElectionSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Election
        fields = (
            "id",
            "organization",
            "organization_name",
            "title",
            "slug",
            "description",
            "status",
            "opens_at",
            "closes_at",
            "results_visibility",
            "publish_results",
            "public_results_enabled",
            "post_vote_access_mode",
            "voter_auto_logout_seconds",
            "voter_results_after_vote_enabled",
            "voter_results_window_starts_at",
            "voter_results_window_ends_at",
            "ballot_instructions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")


class ElectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = (
            "title",
            "slug",
            "description",
            "opens_at",
            "closes_at",
            "results_visibility",
            "publish_results",
            "public_results_enabled",
            "post_vote_access_mode",
            "voter_auto_logout_seconds",
            "voter_results_after_vote_enabled",
            "voter_results_window_starts_at",
            "voter_results_window_ends_at",
            "ballot_instructions",
        )

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        opens_at = attrs.get("opens_at", instance.opens_at if instance else None)
        closes_at = attrs.get("closes_at", instance.closes_at if instance else None)
        voter_results_window_starts_at = attrs.get(
            "voter_results_window_starts_at",
            instance.voter_results_window_starts_at if instance else None,
        )
        voter_results_window_ends_at = attrs.get(
            "voter_results_window_ends_at",
            instance.voter_results_window_ends_at if instance else None,
        )
        if opens_at and closes_at and closes_at <= opens_at:
            raise serializers.ValidationError("closes_at must be later than opens_at.")
        if (
            voter_results_window_starts_at
            and voter_results_window_ends_at
            and voter_results_window_ends_at <= voter_results_window_starts_at
        ):
            raise serializers.ValidationError("voter_results_window_ends_at must be later than voter_results_window_starts_at.")
        return attrs


class ElectionStatusSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("schedule", "close", "archive"))


class ElectionDuplicateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    slug = serializers.SlugField(max_length=140, required=False)


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = (
            "id",
            "election",
            "title",
            "description",
            "max_selections",
            "allow_abstain",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "election", "created_at", "updated_at")


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = (
            "id",
            "post",
            "name",
            "description",
            "image_url",
            "sort_order",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "post", "created_at", "updated_at")
