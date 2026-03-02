from django.urls import path

from voting_system.apps.tokens.views import (
    TokenBatchDeleteView,
    TokenBatchExportCSVView,
    TokenBatchExportPrintView,
    TokenBatchExportQRPrintView,
    TokenBatchExportQRView,
    TokenBatchListCreateView,
    TokenBatchRevokeView,
    TokenBatchTokensView,
    TokenDeleteView,
    TokenVoteResetView,
    UsedTokenBallotListView,
)

urlpatterns = [
    path("org/elections/<uuid:election_id>/token-batches/", TokenBatchListCreateView.as_view(), name="token-batch-list-create"),
    path("org/elections/<uuid:election_id>/used-tokens/", UsedTokenBallotListView.as_view(), name="used-token-list"),
    path("org/token-batches/<uuid:batch_id>/", TokenBatchDeleteView.as_view(), name="token-batch-delete"),
    path("org/token-batches/<uuid:batch_id>/revoke/", TokenBatchRevokeView.as_view(), name="token-batch-revoke"),
    path("org/token-batches/<uuid:batch_id>/tokens/", TokenBatchTokensView.as_view(), name="token-batch-tokens"),
    path("org/tokens/<uuid:token_id>/reset-vote/", TokenVoteResetView.as_view(), name="token-reset-vote"),
    path("org/tokens/<uuid:token_id>/", TokenDeleteView.as_view(), name="token-delete"),
    path("org/token-batches/<uuid:batch_id>/export/csv/", TokenBatchExportCSVView.as_view(), name="token-batch-export-csv"),
    path("org/token-batches/<uuid:batch_id>/export/print/", TokenBatchExportPrintView.as_view(), name="token-batch-export-print"),
    path("org/token-batches/<uuid:batch_id>/export/qr/", TokenBatchExportQRView.as_view(), name="token-batch-export-qr"),
    path("org/token-batches/<uuid:batch_id>/export/qr-print/", TokenBatchExportQRPrintView.as_view(), name="token-batch-export-qr-print"),
]
