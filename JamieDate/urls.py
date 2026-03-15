from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from debug_toolbar.toolbar import debug_toolbar_urls

from .views import api_root_view
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="Jamiedate|| Automated AI Setter digital counterpart",
        default_version="v1",
        description="Jamiedate|| Automated AI Setter digital counterpart",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    path("", api_root_view),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("auth/", include("accounts.urls")),
    path("api/v1/", include("api.urls")),
    path("dashboard/", include("conversation.urls")),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
] + debug_toolbar_urls()
