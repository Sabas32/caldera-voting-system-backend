from django.urls import path

from voting_system.apps.accounts.views import (
    AuthCsrfView,
    AuthChangePasswordView,
    AuthLoginView,
    AuthLogoutView,
    AuthMeView,
    OrgUserListCreateView,
    OrgUserUpdateView,
    SystemOrgAdminCreateView,
)

urlpatterns = [
    path("auth/csrf/", AuthCsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", AuthLoginView.as_view(), name="auth-login"),
    path("auth/logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
    path("auth/change-password/", AuthChangePasswordView.as_view(), name="auth-change-password"),
    path("system/organizations/<uuid:org_id>/admins/", SystemOrgAdminCreateView.as_view(), name="system-org-admins"),
    path("org/users/", OrgUserListCreateView.as_view(), name="org-users"),
    path("org/users/<uuid:membership_id>/", OrgUserUpdateView.as_view(), name="org-user-update"),
]
