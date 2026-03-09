from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Application, Document, Lot, Tender
from .permissions import ApplicationPermission, DocumentPermission, LotPermission, TenderPermission
from .serializers import (
    ApplicationSerializer,
    DocumentSerializer,
    LotSerializer,
    RegisterSerializer,
    TenderSerializer,
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

        base = Tender.objects.select_related("customer").prefetch_related(
            "lots",
            "lots__applications",
            "lots__applications__documents",
        )

        if user.role == "admin":
            return base.all()

        if user.role == "customer":
            return base.filter(customer=user)

        if user.role == "supplier":
            return base.filter(
                Q(status=Tender.STATUS_PUBLISHED, deadline__gt=timezone.now()) |
                Q(status=Tender.STATUS_CLOSED, lots__applications__supplier=user)
            ).distinct()

        return Tender.objects.none()

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Удаление тендера запрещено. Используйте отмену."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        tender = self.get_object()

        if request.user != tender.customer and request.user.role != "admin":
            return Response({"detail": "Нет доступа."}, status=status.HTTP_403_FORBIDDEN)

        if tender.status == Tender.STATUS_CANCELLED:
            return Response({"detail": "Отменённый тендер нельзя публиковать."}, status=status.HTTP_400_BAD_REQUEST)

        if not tender.lots.exists():
            return Response({"detail": "Нельзя публиковать тендер без лотов."}, status=status.HTTP_400_BAD_REQUEST)

        tender.status = Tender.STATUS_PUBLISHED
        tender.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Тендер опубликован."})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        tender = self.get_object()

        if request.user != tender.customer and request.user.role != "admin":
            return Response({"detail": "Нет доступа."}, status=status.HTTP_403_FORBIDDEN)

        if tender.status == Tender.STATUS_CLOSED:
            return Response({"detail": "Закрытый тендер нельзя отменить."}, status=status.HTTP_400_BAD_REQUEST)

        tender.status = Tender.STATUS_CANCELLED
        tender.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Тендер отменён."})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def choose_winner(self, request, pk=None):
        close_expired_tenders()
        tender = self.get_object()

        if request.user != tender.customer and request.user.role != "admin":
            return Response({"detail": "Нет доступа."}, status=status.HTTP_403_FORBIDDEN)

        if tender.status != Tender.STATUS_CLOSED:
            return Response(
                {"detail": "Победителя можно выбрать только после закрытия тендера."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application_id = request.data.get("application_id")
        if not application_id:
            return Response({"detail": "Нужно передать application_id."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            application = Application.objects.select_related("lot", "supplier", "lot__tender").get(
                id=application_id,
                lot__tender=tender,
            )
        except Application.DoesNotExist:
            return Response({"detail": "Заявка не найдена."}, status=status.HTTP_404_NOT_FOUND)

        lot = application.lot
        lot.winner = application.supplier
        lot.save(update_fields=["winner"])

        lot.applications.exclude(id=application.id).update(status=Application.STATUS_LOST)
        application.status = Application.STATUS_WINNER
        application.save(update_fields=["status", "updated_at"])

        return Response({"detail": f"Победитель по лоту {lot.id} выбран."})


class LotViewSet(viewsets.ModelViewSet):
    serializer_class = LotSerializer
    permission_classes = [LotPermission]

    def get_queryset(self):
        close_expired_tenders()
        user = self.request.user
        base = Lot.objects.select_related("tender", "winner").prefetch_related("applications")

        if user.role == "admin":
            return base.all()
        if user.role == "customer":
            return base.filter(tender__customer=user)
        if user.role == "supplier":
            return base.filter(
                Q(tender__status=Tender.STATUS_PUBLISHED, tender__deadline__gt=timezone.now()) |
                Q(applications__supplier=user)
            ).distinct()
        return Lot.objects.none()


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [ApplicationPermission]

    def get_queryset(self):
        close_expired_tenders()
        user = self.request.user
        base = Application.objects.select_related("supplier", "lot", "lot__tender")

        if user.role == "admin":
            return base.all()
        if user.role == "supplier":
            return base.filter(supplier=user)
        if user.role == "customer":
            return base.filter(lot__tender__customer=user)
        return Application.objects.none()

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def withdraw(self, request, pk=None):
        application = self.get_object()

        if request.user != application.supplier and request.user.role != "admin":
            return Response({"detail": "Нет доступа."}, status=status.HTTP_403_FORBIDDEN)

        if application.tender.deadline <= timezone.now():
            return Response(
                {"detail": "Нельзя отозвать заявку после дедлайна."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.status = Application.STATUS_WITHDRAWN
        application.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Заявка отозвана."})


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [DocumentPermission]

    def get_queryset(self):
        user = self.request.user
        base = Document.objects.select_related("application", "application__lot", "application__supplier")

        if user.role == "admin":
            return base.all()
        if user.role == "supplier":
            return base.filter(application__supplier=user)
        if user.role == "customer":
            return base.filter(application__lot__tender__customer=user)
        return Document.objects.none()
