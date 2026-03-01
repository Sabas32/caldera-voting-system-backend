from __future__ import annotations

from rest_framework import serializers


class VoteTokenLoginSerializer(serializers.Serializer):
    token = serializers.CharField(min_length=6, max_length=64)


class BallotSelectionSerializer(serializers.Serializer):
    post_id = serializers.UUIDField()
    candidate_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)
    abstain = serializers.BooleanField(default=False)


class BallotSubmitSerializer(serializers.Serializer):
    selections = BallotSelectionSerializer(many=True)
