from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='supplier')

    def __str__(self):
        return f"{self.username} ({self.role})"


class Tender(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateTimeField()
    requirements = models.TextField(blank=True, null=True)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenders'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_tenders'
    )

    notifications_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active(self):
        return self.status == 'published' and self.deadline > timezone.now()

    def __str__(self):
        return self.title


class Application(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('winner', 'Winner'),
        ('lost', 'Lost'),
        ('withdrawn', 'Withdrawn'),
    )

    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    price = models.DecimalField(max_digits=12, decimal_places=2)
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tender', 'supplier')

    def __str__(self):
        return f"Application #{self.id} for {self.tender.title}"


class Document(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    file = models.FileField(upload_to='documents/')
    description = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for application {self.application_id}"


class VerificationRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    )

    REQUEST_TYPE_CHOICES = (
        ('customer', 'Хочу создавать тендеры'),
        ('supplier', 'Хочу участвовать в тендерах'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_requests'
    )

    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    organization_name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=255, blank=True)
    activity_description = models.TextField()
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50)
    website = models.URLField(blank=True, null=True)
    contact_person = models.CharField(max_length=255)
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Заявка {self.user.username} - {self.request_type}"
