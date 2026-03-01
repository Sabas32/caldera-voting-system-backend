from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/v1/", include("voting_system.apps.accounts.urls")),
    path("api/v1/", include("voting_system.apps.analytics.urls")),
    path("api/v1/", include("voting_system.apps.organizations.urls")),
    path("api/v1/", include("voting_system.apps.elections.urls")),
    path("api/v1/", include("voting_system.apps.tokens.urls")),
    path("api/v1/", include("voting_system.apps.ballots.urls")),
    path("api/v1/", include("voting_system.apps.audit.urls")),
]
