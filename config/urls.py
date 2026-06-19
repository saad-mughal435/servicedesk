"""Root URL configuration.

Routes:
  /admin/                     Django admin
  /api/                       DRF browsable API + JSON (router viewsets)
  /api/auth/token/            DRF token auth (for scripts / curl)
  /api/schema/...             OpenAPI schema + Swagger UI + ReDoc
  /accounts/                  Django auth (login/logout/password)
  /                           Server-rendered service-desk pages
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from apps.accounts.api import TeamViewSet
from apps.assets.api import AssetViewSet
from apps.sla.api import SlaPolicyViewSet
from apps.tickets.api import CategoryViewSet, TicketViewSet

router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="ticket")
router.register("categories", CategoryViewSet, basename="category")
router.register("teams", TeamViewSet, basename="team")
router.register("assets", AssetViewSet, basename="asset")
router.register("sla-policies", SlaPolicyViewSet, basename="slapolicy")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", obtain_auth_token, name="api-token"),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.tickets.urls")),
]
