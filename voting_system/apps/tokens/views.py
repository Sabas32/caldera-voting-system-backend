from __future__ import annotations

from collections import OrderedDict

from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from rest_framework.views import APIView

from voting_system.apps.accounts.models import MembershipRole, OrgMembership
from voting_system.apps.audit.services import log_event
from voting_system.apps.ballots.models import BallotChoice
from voting_system.apps.common.responses import error_response, success_response
from voting_system.apps.elections.models import Election, ElectionStatus
from voting_system.apps.tokens.exports import build_csv_response, build_print_html, build_qr_print_html, build_qr_zip
from voting_system.apps.tokens.models import Token, TokenBatch, TokenStatus
from voting_system.apps.tokens.serializers import (
    TokenBatchCreateSerializer,
    TokenBatchSerializer,
    UsedTokenSerializer,
)
from voting_system.apps.tokens.services import (
    delete_batch_with_tokens,
    delete_token_with_ballot,
    generate_token_batch,
    get_plaintext_tokens_for_export,
    reset_token_vote,
    revoke_batch,
)


def _org_membership(request, organization):
    if getattr(request.user, "is_system_admin", False):
        return None
    return OrgMembership.objects.filter(user=request.user, organization=organization, is_active=True).first()


def _ensure_election_not_archived(election):
    if election.status == ElectionStatus.ARCHIVED:
        return error_response("Archived elections are read-only", status_code=400)
    return None


class TokenBatchListCreateView(APIView):
    def get(self, request, election_id):
        election = Election.objects.filter(id=election_id).select_related("organization").first()
        if not election:
            return error_response("Election not found", status_code=404)
        membership = _org_membership(request, election.organization)
        if not getattr(request.user, "is_system_admin", False) and not membership:
            return error_response("Forbidden", status_code=403)

        batches = TokenBatch.objects.filter(election=election).annotate(
            used_count=Count("tokens", filter=Q(tokens__status="USED")),
            active_count=Count("tokens", filter=Q(tokens__status="ACTIVE")),
        )
        return success_response(TokenBatchSerializer(batches, many=True).data)

    def post(self, request, election_id):
        election = Election.objects.filter(id=election_id).select_related("organization").first()
        if not election:
            return error_response("Election not found", status_code=404)
        archived_error = _ensure_election_not_archived(election)
        if archived_error:
            return archived_error

        membership = _org_membership(request, election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        serializer = TokenBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch, plaintext_tokens = generate_token_batch(
            election=election,
            created_by=request.user,
            label=serializer.validated_data["label"],
            quantity=serializer.validated_data["quantity"],
            expires_at=serializer.validated_data.get("expires_at"),
        )
        data = TokenBatchSerializer(batch).data
        data["tokens"] = plaintext_tokens
        return success_response(data, "Token batch generated", status_code=201)


class TokenBatchTokensView(APIView):
    def get(self, request, batch_id):
        batch = TokenBatch.objects.select_related("election__organization").filter(id=batch_id).first()
        if not batch:
            return error_response("Token batch not found", status_code=404)
        membership = _org_membership(request, batch.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        export_data = get_plaintext_tokens_for_export(batch)
        if not export_data:
            return error_response("Token archive unavailable for this batch.", status_code=404)

        log_event(
            actor=request.user,
            organization=batch.election.organization,
            action="TOKENS_EXPORTED",
            target_type="token_batch",
            target_id=str(batch.id),
            metadata={"format": "view"},
        )
        return success_response(export_data)


class UsedTokenBallotListView(APIView):
    def get(self, request, election_id):
        election = Election.objects.filter(id=election_id).select_related("organization").first()
        if not election:
            return error_response("Election not found", status_code=404)

        membership = _org_membership(request, election.organization)
        if not getattr(request.user, "is_system_admin", False) and not membership:
            return error_response("Forbidden", status_code=403)

        search = (request.query_params.get("search") or "").strip()
        limit_param = request.query_params.get("limit")
        limit = 200
        if limit_param:
            try:
                limit = max(1, min(int(limit_param), 500))
            except (TypeError, ValueError):
                return error_response("Invalid limit value", status_code=400)

        tokens = (
            Token.objects.filter(election=election, status=TokenStatus.USED)
            .select_related("batch", "ballot")
            .prefetch_related(
                Prefetch(
                    "ballot__choices",
                    queryset=BallotChoice.objects.select_related("post", "candidate").order_by(
                        "post__sort_order",
                        "created_at",
                    ),
                )
            )
            .order_by("-used_at")
        )
        if search:
            tokens = tokens.filter(
                Q(token_hint__icontains=search)
                | Q(batch__label__icontains=search)
                | Q(ballot__receipt_code__icontains=search)
                | Q(ballot__choices__post__title__icontains=search)
                | Q(ballot__choices__candidate__name__icontains=search)
            ).distinct()

        data = []
        for token in tokens[:limit]:
            ballot = getattr(token, "ballot", None)
            grouped = OrderedDict()
            if ballot:
                for choice in ballot.choices.all():
                    post_title = choice.post.title
                    if post_title not in grouped:
                        grouped[post_title] = {
                            "post_title": post_title,
                            "abstained": False,
                            "candidate_names": [],
                        }
                    if choice.abstained:
                        grouped[post_title]["abstained"] = True
                        grouped[post_title]["candidate_names"] = []
                    elif choice.candidate:
                        grouped[post_title]["candidate_names"].append(choice.candidate.name)

            data.append(
                {
                    "id": token.id,
                    "token_hint": token.token_hint,
                    "batch_label": token.batch.label,
                    "status": token.status,
                    "used_at": token.used_at,
                    "receipt_code": ballot.receipt_code if ballot else None,
                    "submitted_at": ballot.submitted_at if ballot else None,
                    "selections": list(grouped.values()),
                    "is_resettable": bool(token.status == TokenStatus.USED and not token.batch.revoked),
                }
            )

        serialized = UsedTokenSerializer(data, many=True)
        return success_response({"count": len(serialized.data), "results": serialized.data})


class TokenBatchRevokeView(APIView):
    def post(self, request, batch_id):
        batch = TokenBatch.objects.select_related("election__organization").filter(id=batch_id).first()
        if not batch:
            return error_response("Token batch not found", status_code=404)
        archived_error = _ensure_election_not_archived(batch.election)
        if archived_error:
            return archived_error
        membership = _org_membership(request, batch.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)
        revoke_batch(batch=batch, actor=request.user)
        return success_response(TokenBatchSerializer(batch).data, "Token batch revoked")


class TokenBatchDeleteView(APIView):
    def delete(self, request, batch_id):
        batch = TokenBatch.objects.select_related("election__organization").filter(id=batch_id).first()
        if not batch:
            return error_response("Token batch not found", status_code=404)
        archived_error = _ensure_election_not_archived(batch.election)
        if archived_error:
            return archived_error

        membership = _org_membership(request, batch.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        deleted = delete_batch_with_tokens(batch=batch, actor=request.user)
        return success_response(deleted, "Token batch deleted")


class TokenVoteResetView(APIView):
    def post(self, request, token_id):
        token = Token.objects.select_related("election__organization", "batch").filter(id=token_id).first()
        if not token:
            return error_response("Token not found", status_code=404)
        archived_error = _ensure_election_not_archived(token.election)
        if archived_error:
            return archived_error

        membership = _org_membership(request, token.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        try:
            updated = reset_token_vote(token=token, actor=request.user)
        except ValueError as exc:
            return error_response(str(exc), status_code=400)

        return success_response({"id": str(updated.id), "status": updated.status}, "Token vote reset")


class TokenDeleteView(APIView):
    def delete(self, request, token_id):
        token = Token.objects.select_related("election__organization").filter(id=token_id).first()
        if not token:
            return error_response("Token not found", status_code=404)
        archived_error = _ensure_election_not_archived(token.election)
        if archived_error:
            return archived_error

        membership = _org_membership(request, token.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        deleted = delete_token_with_ballot(token=token, actor=request.user)
        return success_response(deleted, "Token deleted")


class TokenBatchExportCSVView(APIView):
    def get(self, request, batch_id):
        batch = TokenBatch.objects.select_related("election__organization").filter(id=batch_id).first()
        if not batch:
            return error_response("Token batch not found", status_code=404)
        membership = _org_membership(request, batch.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        export_data = get_plaintext_tokens_for_export(batch)
        if not export_data:
            return error_response(
                "Token archive unavailable for this batch.",
                status_code=404,
            )
        rows = [
            {"token": token, "label": export_data["label"], "election_slug": export_data["election_slug"]}
            for token in export_data["tokens"]
        ]
        log_event(
            actor=request.user,
            organization=batch.election.organization,
            action="TOKENS_EXPORTED",
            target_type="token_batch",
            target_id=str(batch.id),
            metadata={"format": "csv"},
        )
        return build_csv_response(f"token_batch_{batch.id}.csv", rows)


class TokenBatchExportPrintView(APIView):
    def get(self, request, batch_id):
        batch = TokenBatch.objects.select_related("election__organization").filter(id=batch_id).first()
        if not batch:
            return error_response("Token batch not found", status_code=404)
        membership = _org_membership(request, batch.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        export_data = get_plaintext_tokens_for_export(batch)
        if not export_data:
            return error_response(
                "Token archive unavailable for this batch.",
                status_code=404,
            )
        log_event(
            actor=request.user,
            organization=batch.election.organization,
            action="TOKENS_EXPORTED",
            target_type="token_batch",
            target_id=str(batch.id),
            metadata={"format": "print"},
        )
        html = build_print_html(batch.label, batch.election.slug, export_data["tokens"])
        return HttpResponse(html, content_type="text/html")


class TokenBatchExportQRView(APIView):
    def get(self, request, batch_id):
        batch = TokenBatch.objects.select_related("election__organization").filter(id=batch_id).first()
        if not batch:
            return error_response("Token batch not found", status_code=404)
        membership = _org_membership(request, batch.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        export_data = get_plaintext_tokens_for_export(batch)
        if not export_data:
            return error_response(
                "Token archive unavailable for this batch.",
                status_code=404,
            )
        log_event(
            actor=request.user,
            organization=batch.election.organization,
            action="TOKENS_EXPORTED",
            target_type="token_batch",
            target_id=str(batch.id),
            metadata={"format": "qr"},
        )
        try:
            payload = build_qr_zip(export_data["tokens"], batch.election.slug)
        except RuntimeError as exc:
            return error_response(str(exc), status_code=501)
        response = HttpResponse(payload, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="token_batch_{batch.id}_qr.zip"'
        return response


class TokenBatchExportQRPrintView(APIView):
    def get(self, request, batch_id):
        batch = TokenBatch.objects.select_related("election__organization").filter(id=batch_id).first()
        if not batch:
            return error_response("Token batch not found", status_code=404)
        membership = _org_membership(request, batch.election.organization)
        if not getattr(request.user, "is_system_admin", False):
            if not membership or membership.role not in (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER):
                return error_response("Forbidden", status_code=403)

        export_data = get_plaintext_tokens_for_export(batch)
        if not export_data:
            return error_response(
                "Token archive unavailable for this batch.",
                status_code=404,
            )
        log_event(
            actor=request.user,
            organization=batch.election.organization,
            action="TOKENS_EXPORTED",
            target_type="token_batch",
            target_id=str(batch.id),
            metadata={"format": "qr_print"},
        )
        try:
            html = build_qr_print_html(batch.label, batch.election.slug, export_data["tokens"])
        except RuntimeError as exc:
            return error_response(str(exc), status_code=501)
        return HttpResponse(html, content_type="text/html")
