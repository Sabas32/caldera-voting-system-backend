from __future__ import annotations

from rest_framework import serializers

from voting_system.apps.tokens.models import TokenBatch


class TokenBatchCreateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120)
    quantity = serializers.IntegerField(min_value=1, max_value=10000)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class TokenBatchSerializer(serializers.ModelSerializer):
    used_count = serializers.IntegerField(read_only=True)
    active_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TokenBatch
        fields = (
            "id",
            "election",
            "label",
            "quantity",
            "expires_at",
            "revoked",
            "created_at",
            "used_count",
            "active_count",
        )


class UsedTokenSelectionSerializer(serializers.Serializer):
    post_title = serializers.CharField()
    abstained = serializers.BooleanField()
    candidate_names = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class UsedTokenSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    token_hint = serializers.CharField()
    batch_label = serializers.CharField()
    status = serializers.CharField()
    used_at = serializers.DateTimeField(allow_null=True)
    receipt_code = serializers.CharField(allow_null=True)
    submitted_at = serializers.DateTimeField(allow_null=True)
    selections = UsedTokenSelectionSerializer(many=True)
    is_resettable = serializers.BooleanField()
