from __future__ import annotations

from datetime import timedelta

from django.db import connection
from django.utils import timezone
from rest_framework.views import APIView

from voting_system.apps.accounts.models import OrgMembership
from voting_system.apps.audit.models import AuditLog
from voting_system.apps.audit.serializers import AuditLogSerializer
from voting_system.apps.ballots.models import Ballot
from voting_system.apps.common.responses import error_response, success_response
from voting_system.apps.elections.models import Election
from voting_system.apps.organizations.models import Organization
from voting_system.apps.tokens.models import Token, TokenStatus


def _resolve_org(request):
    org_id = request.headers.get("X-Org-Id") or request.query_params.get("org_id")
    if not org_id:
        return None
    return Organization.objects.filter(id=org_id).first()


class SystemDashboardView(APIView):
    def get(self, request):
        if not getattr(request.user, "is_system_admin", False):
            return error_response("Forbidden", status_code=403)

        since = timezone.now() - timedelta(days=7)
        recent_audit = AuditLog.objects.select_related("organization", "actor").all()[:20]
        payload = {
            "total_organizations": Organization.objects.count(),
            "live_elections": Election.objects.filter(status="LIVE").count(),
            "ballots_last_7_days": Ballot.objects.filter(submitted_at__gte=since).count(),
            "tokens_used_last_7_days": Token.objects.filter(status=TokenStatus.USED, used_at__gte=since).count(),
            "recent_audit": AuditLogSerializer(recent_audit, many=True).data,
        }
        return success_response(payload)


class OrgDashboardView(APIView):
    def get(self, request):
        organization = _resolve_org(request)
        if not organization:
            return error_response("Organization context missing", status_code=400)

        membership = OrgMembership.objects.filter(user=request.user, organization=organization, is_active=True).first()
        if not membership and not getattr(request.user, "is_system_admin", False):
            return error_response("Forbidden", status_code=403)

        recent_elections = (
            Election.objects.filter(organization=organization)
            .order_by("-created_at")
            .values("id", "title", "slug", "status", "opens_at", "closes_at")[:5]
        )
        recent_audit = (
            AuditLog.objects.select_related("organization", "actor")
            .filter(organization=organization)
            .order_by("-created_at")[:20]
        )

        tokens_generated = Token.objects.filter(election__organization=organization).count()
        tokens_used = Token.objects.filter(election__organization=organization, status=TokenStatus.USED).count()
        ballots_submitted = Ballot.objects.filter(election__organization=organization).count()
        turnout = round((tokens_used / tokens_generated * 100), 2) if tokens_generated else 0

        payload = {
            "active_elections": Election.objects.filter(organization=organization, status="LIVE").count(),
            "tokens_generated": tokens_generated,
            "tokens_used": tokens_used,
            "ballots_submitted": ballots_submitted,
            "turnout_percentage": turnout,
            "recent_elections": list(recent_elections),
            "recent_audit": AuditLogSerializer(recent_audit, many=True).data,
        }
        return success_response(payload)


class SystemHealthView(APIView):
    def get(self, request):
        if not getattr(request.user, "is_system_admin", False):
            return error_response("Forbidden", status_code=403)

        db_status = "UP"
        db_error = None
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
            if not row or row[0] != 1:
                raise RuntimeError("Database health probe returned unexpected payload.")
        except Exception as exc:
            db_status = "DOWN"
            db_error = str(exc)

        payload = {
            "status": "UP" if db_status == "UP" else "DEGRADED",
            "api": "UP",
            "database": db_status,
            "database_error": db_error,
            "checked_at": timezone.now().isoformat(),
        }

        return success_response(payload)
