from __future__ import annotations

from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.views import APIView

from voting_system.apps.accounts.models import MembershipRole, OrgMembership
from voting_system.apps.accounts.permissions import IsSystemAdmin
from voting_system.apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    MembershipSerializer,
    OrgMembershipCreateSerializer,
    OrgMembershipUpdateSerializer,
    UserSerializer,
)
from voting_system.apps.accounts.services import create_or_update_membership, update_membership
from voting_system.apps.common.responses import error_response, success_response
from voting_system.apps.organizations.models import Organization


def _resolve_org(request):
    org_id = request.headers.get("X-Org-Id") or request.query_params.get("org_id")
    if not org_id:
        return None
    return Organization.objects.filter(id=org_id).first()


def _can_manage_org_users(*, request, organization):
    if getattr(request.user, "is_system_admin", False):
        return True
    membership = OrgMembership.objects.filter(
        user=request.user,
        organization=organization,
        is_active=True,
        role=MembershipRole.ORG_ADMIN,
    ).first()
    return membership is not None


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AuthLoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return success_response(UserSerializer(user).data, "Logged in")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AuthCsrfView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request):
        return success_response({"csrf_token": get_token(request)})


class AuthLogoutView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request):
        logout(request)
        return success_response(message="Logged out")

    def post(self, request):
        logout(request)
        return success_response(message="Logged out")


class AuthMeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return success_response(None, "Not authenticated")
        return success_response(UserSerializer(request.user).data)


class AuthChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password", "updated_at"])
        return success_response(message="Password updated successfully")


class SystemOrgAdminCreateView(APIView):
    permission_classes = (IsSystemAdmin,)

    def post(self, request, org_id):
        org = Organization.objects.filter(id=org_id).first()
        if not org:
            return error_response("Organization not found", status_code=404)

        serializer = OrgMembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, generated_password = create_or_update_membership(
            organization=org,
            payload=serializer.validated_data,
            actor=request.user,
        )
        data = MembershipSerializer(membership).data
        if generated_password:
            data["generated_password"] = generated_password
        return success_response(data, "Organization user saved", status.HTTP_201_CREATED)


class OrgUserListCreateView(APIView):
    def get(self, request):
        organization = _resolve_org(request)
        if not organization:
            return error_response("Organization context missing", status_code=400)
        if not _can_manage_org_users(request=request, organization=organization):
            return error_response("Forbidden", status_code=403)

        memberships = OrgMembership.objects.filter(organization=organization).select_related("user", "organization")
        return success_response(MembershipSerializer(memberships, many=True).data)

    def post(self, request):
        organization = _resolve_org(request)
        if not organization:
            return error_response("Organization context missing", status_code=400)
        if not _can_manage_org_users(request=request, organization=organization):
            return error_response("Forbidden", status_code=403)

        serializer = OrgMembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, generated_password = create_or_update_membership(
            organization=organization,
            payload=serializer.validated_data,
            actor=request.user,
        )
        data = MembershipSerializer(membership).data
        if generated_password:
            data["generated_password"] = generated_password
        return success_response(data, "Organization user saved", status.HTTP_201_CREATED)


class OrgUserUpdateView(APIView):
    def patch(self, request, membership_id):
        membership = OrgMembership.objects.select_related("organization").filter(id=membership_id).first()
        if not membership:
            return error_response("Membership not found", status_code=404)
        if not _can_manage_org_users(request=request, organization=membership.organization):
            return error_response("Forbidden", status_code=403)

        serializer = OrgMembershipUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        membership, generated_password = update_membership(
            membership=membership,
            payload=serializer.validated_data,
            actor=request.user,
        )
        data = MembershipSerializer(membership).data
        if generated_password:
            data["generated_password"] = generated_password
        return success_response(data, "Membership updated")
