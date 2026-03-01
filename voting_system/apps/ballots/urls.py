from django.urls import path

from voting_system.apps.ballots.views import (
    VoteBallotView,
    VoteLogoutView,
    VotePublicResultsView,
    VoteStatusView,
    VoteSubmitView,
    VoteTokenLoginView,
)

urlpatterns = [
    path("vote/token-login/", VoteTokenLoginView.as_view(), name="vote-token-login"),
    path("vote/logout/", VoteLogoutView.as_view(), name="vote-logout"),
    path("vote/elections/<slug:slug>/ballot/", VoteBallotView.as_view(), name="vote-ballot"),
    path("vote/elections/<slug:slug>/submit/", VoteSubmitView.as_view(), name="vote-submit"),
    path("vote/elections/<slug:slug>/status/", VoteStatusView.as_view(), name="vote-status"),
    path("vote/elections/<slug:slug>/results/", VotePublicResultsView.as_view(), name="vote-results"),
]
