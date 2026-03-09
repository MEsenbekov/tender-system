from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TenderViewSet, ApplicationViewSet, DocumentViewSet, RegisterView, ProfileView

router = DefaultRouter()
router.register(r'tenders', TenderViewSet, basename='tender')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('auth/profile/', ProfileView.as_view(), name='api_profile'),
    path('', include(router.urls)),
]
