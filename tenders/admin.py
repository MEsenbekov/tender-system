from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Application, Document, Lot, Tender, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("id",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Роль в системе", {"fields": ("role",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Роль в системе", {"fields": ("role",)}),
    )


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0


class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0
    readonly_fields = ("supplier", "price", "comment", "status", "created_at", "updated_at")
    can_delete = False


class LotInline(admin.TabularInline):
    model = Lot
    extra = 0


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "customer", "status", "deadline", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "customer__username", "customer__email")
    ordering = ("-created_at",)
    autocomplete_fields = ("customer",)
    inlines = [LotInline]


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "tender", "quantity", "unit", "winner")
    search_fields = ("title", "description", "tender__title")
    autocomplete_fields = ("tender", "winner")
    inlines = [ApplicationInline]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "lot", "supplier", "price", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("lot__title", "lot__tender__title", "supplier__username", "supplier__email")
    ordering = ("-created_at",)
    autocomplete_fields = ("lot", "supplier")
    inlines = [DocumentInline]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "description", "uploaded_at")
    search_fields = ("description", "application__lot__title", "application__supplier__username")
    ordering = ("-uploaded_at",)
    autocomplete_fields = ("application",)