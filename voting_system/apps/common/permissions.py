from __future__ import annotations

from rest_framework import permissions

from voting_system.apps.accounts.models import MembershipRole, OrgMembership


class IsSystemAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, "is_system_admin", False))


class HasOrgRole(permissions.BasePermission):
    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        org = getattr(view, "organization", None)
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_system_admin", False):
            return True
        if not org:
            return False
        membership = OrgMembership.objects.filter(
            user=request.user,
            organization=org,
            is_active=True,
        ).first()
        if not membership:
            return False
        if not self.allowed_roles:
            return True
        return membership.role in self.allowed_roles


class IsOrgViewer(HasOrgRole):
    allowed_roles = (
        MembershipRole.ORG_ADMIN,
        MembershipRole.ELECTION_MANAGER,
        MembershipRole.RESULTS_VIEWER,
    )


class IsOrgEditor(HasOrgRole):
    allowed_roles = (MembershipRole.ORG_ADMIN, MembershipRole.ELECTION_MANAGER)


class IsOrgAdmin(HasOrgRole):
    allowed_roles = (MembershipRole.ORG_ADMIN,)
