from __future__ import annotations

from django.db.models import Count, Q
from rest_framework.views import APIView

from voting_system.apps.accounts.models import MembershipRole, OrgMembership
from voting_system.apps.common.responses import error_response, success_response
from voting_system.apps.organizations.models import Organization
from voting_system.apps.organizations.permissions import IsSystemAdmin
from voting_system.apps.organizations.serializers import OrganizationSerializer
from voting_system.apps.organizations.services import log_org_created, log_org_updated


def _resolve_org(request):
    org_id = request.headers.get("X-Org-Id") or request.query_params.get("org_id")
    if not org_id:
        return None
    return Organization.objects.filter(id=org_id).first()


def _can_manage_org_settings(*, request, organization):
    if getattr(request.user, "is_system_admin", False):
        return True
    membership = OrgMembership.objects.filter(
        user=request.user,
        organization=organization,
        is_active=True,
        role=MembershipRole.ORG_ADMIN,
    ).first()
    return membership is not None


class SystemOrganizationListCreateView(APIView):
    permission_classes = (IsSystemAdmin,)

    def get(self, request):
        queryset = Organization.objects.annotate(active_elections=Count("elections", filter=Q(elections__status="LIVE")))
        query = (request.query_params.get("search") or "").strip()
        status = (request.query_params.get("status") or "").strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(slug__icontains=query))
        if status:
            queryset = queryset.filter(status=status)
        return success_response(OrganizationSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        log_org_created(actor=request.user, organization=org)
        return success_response(OrganizationSerializer(org).data, "Organization created", 201)


class SystemOrganizationDetailView(APIView):
    permission_classes = (IsSystemAdmin,)

    def get(self, request, org_id):
        org = Organization.objects.filter(id=org_id).first()
        if not org:
            return error_response("Organization not found", status_code=404)
        return success_response(OrganizationSerializer(org).data)

    def patch(self, request, org_id):
        org = Organization.objects.filter(id=org_id).first()
        if not org:
            return error_response("Organization not found", status_code=404)
        serializer = OrganizationSerializer(org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        log_org_updated(actor=request.user, organization=org)
        return success_response(OrganizationSerializer(org).data, "Organization updated")


class OrgSettingsView(APIView):
    def get(self, request):
        organization = _resolve_org(request)
        if not organization:
            return error_response("Organization context missing", status_code=400)

        membership = OrgMembership.objects.filter(user=request.user, organization=organization, is_active=True).first()
        if not membership and not getattr(request.user, "is_system_admin", False):
            return error_response("Forbidden", status_code=403)

        return success_response(OrganizationSerializer(organization).data)

    def patch(self, request):
        organization = _resolve_org(request)
        if not organization:
            return error_response("Organization context missing", status_code=400)
        if not _can_manage_org_settings(request=request, organization=organization):
            return error_response("Forbidden", status_code=403)

        allowed_fields = {
            "name",
            "primary_color_override",
            "logo_url",
            "default_public_results_enabled",
            "default_results_visibility",
            "voter_auto_logout_seconds",
            "default_voter_results_after_vote_enabled",
            "default_voter_results_view_window_seconds",
        }
        payload = {key: value for key, value in request.data.items() if key in allowed_fields}
        serializer = OrganizationSerializer(organization, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        organization = serializer.save()
        log_org_updated(actor=request.user, organization=organization)
        return success_response(OrganizationSerializer(organization).data, "Organization settings updated")
