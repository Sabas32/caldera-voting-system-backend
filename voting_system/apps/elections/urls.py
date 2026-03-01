from django.urls import path

from voting_system.apps.elections.views import (
    OrgCandidateDetailView,
    OrgCandidateListCreateView,
    OrgElectionDetailView,
    OrgElectionDuplicateView,
    OrgElectionExportExcelView,
    OrgElectionListCreateView,
    OrgElectionPublishResultsView,
    OrgElectionResultsView,
    OrgElectionStatusActionView,
    OrgPostDetailView,
    OrgPostListCreateView,
)

urlpatterns = [
    path("org/elections/", OrgElectionListCreateView.as_view(), name="org-elections"),
    path("org/elections/<uuid:election_id>/", OrgElectionDetailView.as_view(), name="org-election-detail"),
    path("org/elections/<uuid:election_id>/status/", OrgElectionStatusActionView.as_view(), name="org-election-status"),
    path("org/elections/<uuid:election_id>/posts/", OrgPostListCreateView.as_view(), name="org-posts"),
    path("org/posts/<uuid:post_id>/", OrgPostDetailView.as_view(), name="org-post-detail"),
    path("org/posts/<uuid:post_id>/candidates/", OrgCandidateListCreateView.as_view(), name="org-candidates"),
    path("org/candidates/<uuid:candidate_id>/", OrgCandidateDetailView.as_view(), name="org-candidate-detail"),
    path("org/elections/<uuid:election_id>/results/", OrgElectionResultsView.as_view(), name="org-election-results"),
    path(
        "org/elections/<uuid:election_id>/publish-results/",
        OrgElectionPublishResultsView.as_view(),
        name="org-election-publish-results",
    ),
    path(
        "org/elections/<uuid:election_id>/export/excel/",
        OrgElectionExportExcelView.as_view(),
        name="org-election-export-excel",
    ),
    path(
        "org/elections/<uuid:election_id>/duplicate/",
        OrgElectionDuplicateView.as_view(),
        name="org-election-duplicate",
    ),
]
