from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_CUSTOMER = "customer"
    ROLE_SUPPLIER = "supplier"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_SUPPLIER, "Supplier"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_SUPPLIER)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Tender(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CLOSED = "closed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateTimeField()
    requirements = models.TextField(blank=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenders",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def is_active(self):
        return self.status == self.STATUS_PUBLISHED and self.deadline > timezone.now()

    def clean(self):
        if self.deadline and self.deadline <= timezone.now() and self.pk is None:
            raise ValidationError({"deadline": "Дата окончания подачи заявок должна быть в будущем."})

    def __str__(self):
        return self.title


class Lot(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="lots")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=50, blank=True)
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_lots",
    )

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.tender.title} / {self.title}"


class Application(models.Model):
    STATUS_PENDING = "pending"
    STATUS_WINNER = "winner"
    STATUS_LOST = "lost"
    STATUS_WITHDRAWN = "withdrawn"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_WINNER, "Winner"),
        (STATUS_LOST, "Lost"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    )

    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="applications")
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("price", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("lot", "supplier"),
                name="unique_application_per_supplier_per_lot",
            )
        ]

    @property
    def tender(self):
        return self.lot.tender

    def can_edit(self):
        return self.tender.deadline > timezone.now() and self.status != self.STATUS_WITHDRAWN

    def __str__(self):
        return f"Application #{self.pk} for lot {self.lot_id}"


class Document(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)

    def __str__(self):
        return f"Document for application {self.application_id}"
