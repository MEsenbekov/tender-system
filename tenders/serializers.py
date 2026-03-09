from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import Tender, Application, Document

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('Пароли не совпадают.')
        return attrs

    def validate_role(self, value):
        if value not in ['customer', 'supplier']:
            raise serializers.ValidationError('Можно зарегистрировать только customer или supplier.')
        return value

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'application', 'file', 'description', 'uploaded_at']
        read_only_fields = ['uploaded_at']


class ApplicationSerializer(serializers.ModelSerializer):
    supplier = UserSerializer(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = [
            'id',
            'tender',
            'supplier',
            'price',
            'comment',
            'status',
            'created_at',
            'updated_at',
            'documents',
        ]
        read_only_fields = ['supplier', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        request = self.context['request']
        tender = attrs.get('tender', getattr(self.instance, 'tender', None))

        if not tender:
            raise serializers.ValidationError('Тендер обязателен.')

        if tender.status != 'published':
            raise serializers.ValidationError('Можно подавать заявку только на опубликованный тендер.')

        if tender.deadline <= timezone.now():
            raise serializers.ValidationError('Срок подачи заявок уже истёк.')

        if request.user.role not in ['supplier', 'admin']:
            raise serializers.ValidationError('Только поставщик может работать с заявками.')

        return attrs

    def create(self, validated_data):
        validated_data['supplier'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.tender.deadline <= timezone.now():
            raise serializers.ValidationError('После дедлайна заявку менять нельзя.')

        if instance.status == 'withdrawn':
            raise serializers.ValidationError('Отозванную заявку менять нельзя.')

        return super().update(instance, validated_data)


class TenderSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    applications = ApplicationSerializer(many=True, read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Tender
        fields = [
            'id',
            'title',
            'description',
            'deadline',
            'requirements',
            'customer',
            'status',
            'winner',
            'notifications_sent',
            'created_at',
            'is_active',
            'applications',
        ]
        read_only_fields = ['customer', 'winner', 'notifications_sent', 'created_at']

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('Deadline должен быть в будущем.')
        return value

    def update(self, instance, validated_data):
        if instance.applications.exists():
            raise serializers.ValidationError(
                'Нельзя редактировать тендер после появления заявок. Можно только отменить.'
            )
        return super().update(instance, validated_data)
