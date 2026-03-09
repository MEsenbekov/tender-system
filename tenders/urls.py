from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApplicationViewSet,
    DocumentViewSet,
    LotViewSet,
    ProfileView,
    RegisterView,
    TenderViewSet,
)

router = DefaultRouter()
router.register(r"tenders", TenderViewSet, basename="tender")
router.register(r"lots", LotViewSet, basename="lot")
router.register(r"applications", ApplicationViewSet, basename="application")
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/profile/", ProfileView.as_view(), name="api-profile"),
    path("", include(router.urls)),
]
