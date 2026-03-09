from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import Application, Document, Lot, Tender

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Пароли не совпадают."})
        return attrs

    def validate_role(self, value):
        if value not in [User.ROLE_CUSTOMER, User.ROLE_SUPPLIER]:
            raise serializers.ValidationError("Можно зарегистрировать только customer или supplier.")
        return value

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "application", "file", "description", "uploaded_at"]
        read_only_fields = ["uploaded_at"]

    def validate_application(self, application):
        request = self.context["request"]

        if request.user.role == "supplier" and application.supplier_id != request.user.id:
            raise serializers.ValidationError("Нельзя загружать документы в чужую заявку.")

        if application.tender.deadline <= timezone.now():
            raise serializers.ValidationError("После дедлайна загружать документы нельзя.")

        return application


class ApplicationSerializer(serializers.ModelSerializer):
    supplier = UserSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    lot_id = serializers.PrimaryKeyRelatedField(source="lot", queryset=Lot.objects.all(), write_only=True)
    tender_id = serializers.IntegerField(source="lot.tender_id", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "lot",
            "lot_id",
            "tender_id",
            "supplier",
            "price",
            "comment",
            "status",
            "created_at",
            "updated_at",
            "documents",
        ]
        read_only_fields = ["lot", "supplier", "status", "created_at", "updated_at", "tender_id"]

    def validate(self, attrs):
        request = self.context["request"]
        lot = attrs.get("lot", getattr(self.instance, "lot", None))

        if not lot:
            raise serializers.ValidationError("Лот обязателен.")

        tender = lot.tender

        if tender.status != Tender.STATUS_PUBLISHED:
            raise serializers.ValidationError("Можно подавать заявку только на опубликованный тендер.")

        if tender.deadline <= timezone.now():
            raise serializers.ValidationError("Срок подачи заявок уже истёк.")

        if request.user.role not in [User.ROLE_SUPPLIER, User.ROLE_ADMIN]:
            raise serializers.ValidationError("Только поставщик может работать с заявками.")

        if self.instance is None:
            already_exists = Application.objects.filter(
                lot=lot,
                supplier=request.user
            ).exists()
            if already_exists:
                raise serializers.ValidationError(
                    {"detail": "Вы уже подали заявку на этот лот."}
                )

        return attrs

    def create(self, validated_data):
        validated_data["supplier"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if not instance.can_edit():
            raise serializers.ValidationError("После дедлайна или отзыва заявку менять нельзя.")

        if "lot" in validated_data and validated_data["lot"].id != instance.lot_id:
            raise serializers.ValidationError("Нельзя менять лот у существующей заявки.")

        return super().update(instance, validated_data)


class LotSerializer(serializers.ModelSerializer):
    winner = UserSerializer(read_only=True)
    applications = ApplicationSerializer(many=True, read_only=True)

    class Meta:
        model = Lot
        fields = [
            "id",
            "tender",
            "title",
            "description",
            "quantity",
            "unit",
            "winner",
            "applications",
        ]
        read_only_fields = ["winner"]

    def validate_tender(self, tender):
        if tender.status in [Tender.STATUS_CLOSED, Tender.STATUS_CANCELLED]:
            raise serializers.ValidationError("Нельзя добавлять лоты в закрытый или отменённый тендер.")
        return tender


class TenderSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    lots = LotSerializer(many=True, read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Tender
        fields = [
            "id",
            "title",
            "description",
            "deadline",
            "requirements",
            "customer",
            "status",
            "created_at",
            "updated_at",
            "is_active",
            "lots",
        ]
        read_only_fields = ["customer", "created_at", "updated_at"]

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Deadline должен быть в будущем.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        if instance and instance.status in [Tender.STATUS_CLOSED, Tender.STATUS_CANCELLED]:
            raise serializers.ValidationError("Закрытый или отменённый тендер нельзя редактировать.")

        return attrs

    def update(self, instance, validated_data):
        if instance.lots.filter(applications__isnull=False).exists():
            raise serializers.ValidationError("Нельзя редактировать тендер после появления заявок. Можно только отменить.")

        return super().update(instance, validated_data)
