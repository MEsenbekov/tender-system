from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Tender, Application, Document
from .permissions import TenderPermission, ApplicationPermission, DocumentPermission
from .serializers import (
    TenderSerializer,
    ApplicationSerializer,
    DocumentSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import close_expired_tenders


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class TenderViewSet(viewsets.ModelViewSet):
    serializer_class = TenderSerializer
    permission_classes = [TenderPermission]

    def get_queryset(self):
        close_expired_tenders()
        user = self.request.user

        if user.role == 'admin':
            return Tender.objects.all().order_by('-created_at')

        if user.role == 'customer':
            return Tender.objects.filter(customer=user).order_by('-created_at')

        if user.role == 'supplier':
            return Tender.objects.filter(
                status='published',
                deadline__gt=timezone.now()
            ).order_by('-created_at')

        return Tender.objects.none()

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'Удаление тендера запрещено. Используйте отмену.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        tender = self.get_object()

        if request.user != tender.customer and request.user.role != 'admin':
            return Response({'detail': 'Нет доступа.'}, status=status.HTTP_403_FORBIDDEN)

        if tender.status == 'cancelled':
            return Response({'detail': 'Отменённый тендер нельзя публиковать.'}, status=400)

        tender.status = 'published'
        tender.notifications_sent = False
        tender.save()
        return Response({'detail': 'Тендер опубликован.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        tender = self.get_object()

        if request.user != tender.customer and request.user.role != 'admin':
            return Response({'detail': 'Нет доступа.'}, status=status.HTTP_403_FORBIDDEN)

        tender.status = 'cancelled'
        tender.save()
        return Response({'detail': 'Тендер отменён.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def choose_winner(self, request, pk=None):
        close_expired_tenders()
        tender = self.get_object()

        if request.user != tender.customer and request.user.role != 'admin':
            return Response({'detail': 'Нет доступа.'}, status=status.HTTP_403_FORBIDDEN)

        if tender.status != 'closed':
            return Response(
                {'detail': 'Победителя можно выбрать только после закрытия тендера.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        application_id = request.data.get('application_id')
        if not application_id:
            return Response({'detail': 'Нужно передать application_id.'}, status=400)

        try:
            application = tender.applications.get(id=application_id)
        except Application.DoesNotExist:
            return Response({'detail': 'Заявка не найдена.'}, status=404)

        tender.winner = application.supplier
        tender.save()

        tender.applications.exclude(id=application.id).update(status='lost')
        application.status = 'winner'
        application.save()

        return Response({'detail': 'Победитель выбран.'})


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [ApplicationPermission]

    def get_queryset(self):
        close_expired_tenders()
        user = self.request.user

        if user.role == 'admin':
            return Application.objects.all().order_by('-created_at')

        if user.role == 'supplier':
            return Application.objects.filter(supplier=user).order_by('-created_at')

        if user.role == 'customer':
            return Application.objects.filter(tender__customer=user).order_by('-created_at')

        return Application.objects.none()

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        application = self.get_object()

        if request.user != application.supplier and request.user.role != 'admin':
            return Response({'detail': 'Нет доступа.'}, status=status.HTTP_403_FORBIDDEN)

        if application.tender.deadline <= timezone.now():
            return Response(
                {'detail': 'Нельзя отозвать заявку после дедлайна.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = 'withdrawn'
        application.save()
        return Response({'detail': 'Заявка отозвана.'})


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [DocumentPermission]

    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            return Document.objects.all().order_by('-uploaded_at')

        if user.role == 'supplier':
            return Document.objects.filter(application__supplier=user).order_by('-uploaded_at')

        if user.role == 'customer':
            return Document.objects.filter(application__tender__customer=user).order_by('-uploaded_at')

        return Document.objects.none()

    def perform_create(self, serializer):
        application = serializer.validated_data['application']

        if self.request.user.role == 'supplier' and application.supplier != self.request.user:
            raise PermissionError('Нельзя загружать документы в чужую заявку.')

        if application.tender.deadline <= timezone.now():
            raise ValueError('После дедлайна загружать документы нельзя.')

        serializer.save()
