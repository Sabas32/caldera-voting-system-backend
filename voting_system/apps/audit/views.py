from __future__ import annotations

from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView

from voting_system.apps.accounts.models import OrgMembership
from voting_system.apps.audit.models import AuditLog
from voting_system.apps.audit.serializers import AuditLogSerializer
from voting_system.apps.common.responses import error_response, success_response


def _apply_filters(request, queryset):
    org_id = request.query_params.get("org_id")
    action = request.query_params.get("action")
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if org_id:
        queryset = queryset.filter(organization_id=org_id)
    if action:
        queryset = queryset.filter(action=action)
    if date_from:
        parsed_from = parse_datetime(date_from)
        if parsed_from:
            queryset = queryset.filter(created_at__gte=parsed_from)
    if date_to:
        parsed_to = parse_datetime(date_to)
        if parsed_to:
            queryset = queryset.filter(created_at__lte=parsed_to)
    return queryset


class SystemAuditListView(APIView):
    def get(self, request):
        if not getattr(request.user, "is_system_admin", False):
            return error_response("Forbidden", status_code=403)
        logs = _apply_filters(request, AuditLog.objects.select_related("organization", "actor"))
        return success_response(AuditLogSerializer(logs[:500], many=True).data)


class OrgAuditListView(APIView):
    def get(self, request):
        org_id = request.headers.get("X-Org-Id") or request.query_params.get("org_id")
        if not org_id:
            return error_response("Organization context missing", status_code=400)

        membership = OrgMembership.objects.filter(user=request.user, organization_id=org_id, is_active=True).first()
        if not membership and not getattr(request.user, "is_system_admin", False):
            return error_response("Forbidden", status_code=403)

        logs = AuditLog.objects.select_related("organization", "actor").filter(organization_id=org_id)
        logs = _apply_filters(request, logs)
        return success_response(AuditLogSerializer(logs[:500], many=True).data)
