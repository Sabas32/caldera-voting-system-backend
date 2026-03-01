from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers

from voting_system.apps.accounts.models import MembershipRole, OrgMembership, User


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_first_name = serializers.CharField(source="user.first_name", read_only=True)
    user_last_name = serializers.CharField(source="user.last_name", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = OrgMembership
        fields = (
            "id",
            "user_email",
            "user_first_name",
            "user_last_name",
            "organization",
            "organization_name",
            "organization_slug",
            "role",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class UserSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_system_admin",
            "memberships",
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(request=self.context.get("request"), email=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("User is deactivated")
        attrs["user"] = user
        return attrs


class OrgMembershipCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, required=False)
    role = serializers.ChoiceField(choices=MembershipRole.choices)


class OrgMembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=MembershipRole.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    reset_password = serializers.BooleanField(required=False, default=False)
    password = serializers.CharField(min_length=8, required=False)

    def validate(self, attrs):
        if attrs.get("password") and not attrs.get("reset_password", False):
            raise serializers.ValidationError("reset_password must be true when password is provided.")
        return attrs
