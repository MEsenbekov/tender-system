from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Tender, Application, Document, VerificationRequest


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'role',
        'is_staff',
        'is_active',
    )
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('id',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Роль в системе', {'fields': ('role',)}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Роль в системе', {'fields': ('role',)}),
    )


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0


class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0
    readonly_fields = ('supplier', 'price', 'comment', 'status', 'created_at', 'updated_at')
    can_delete = False


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'customer',
        'status',
        'winner',
        'deadline',
        'notifications_sent',
        'created_at',
    )
    list_filter = ('status', 'notifications_sent', 'created_at')
    search_fields = ('title', 'description', 'customer__username', 'customer__email')
    ordering = ('-created_at',)
    autocomplete_fields = ('customer', 'winner')
    inlines = [ApplicationInline]

    actions = ['publish_tenders', 'close_tenders', 'cancel_tenders']

    @admin.action(description='Опубликовать выбранные тендеры')
    def publish_tenders(self, request, queryset):
        updated = queryset.update(status='published', notifications_sent=False)
        self.message_user(request, f'Опубликовано тендеров: {updated}')

    @admin.action(description='Закрыть выбранные тендеры')
    def close_tenders(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'Закрыто тендеров: {updated}')

    @admin.action(description='Отменить выбранные тендеры')
    def cancel_tenders(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'Отменено тендеров: {updated}')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tender',
        'supplier',
        'price',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = (
        'tender__title',
        'supplier__username',
        'supplier__email',
        'comment',
    )
    ordering = ('-created_at',)
    autocomplete_fields = ('tender', 'supplier')
    inlines = [DocumentInline]

    actions = ['mark_pending', 'mark_winner', 'mark_lost', 'mark_withdrawn']

    @admin.action(description='Отметить как pending')
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'Обновлено заявок: {updated}')

    @admin.action(description='Отметить как winner')
    def mark_winner(self, request, queryset):
        count = 0
        for app in queryset:
            app.status = 'winner'
            app.save()
            app.tender.winner = app.supplier
            app.tender.status = 'closed'
            app.tender.save()
            app.tender.applications.exclude(id=app.id).update(status='lost')
            count += 1
        self.message_user(request, f'Победителей отмечено: {count}')

    @admin.action(description='Отметить как lost')
    def mark_lost(self, request, queryset):
        updated = queryset.update(status='lost')
        self.message_user(request, f'Проигравших заявок: {updated}')

    @admin.action(description='Отметить как withdrawn')
    def mark_withdrawn(self, request, queryset):
        updated = queryset.update(status='withdrawn')
        self.message_user(request, f'Отозванных заявок: {updated}')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'description', 'uploaded_at')
    search_fields = (
        'description',
        'application__tender__title',
        'application__supplier__username',
    )
    ordering = ('-uploaded_at',)
    autocomplete_fields = ('application',)


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'request_type',
        'organization_name',
        'phone',
        'status',
        'created_at',
    )
    list_filter = ('request_type', 'status', 'created_at')
    search_fields = (
        'user__username',
        'user__email',
        'organization_name',
        'contact_person',
        'phone',
    )
    ordering = ('-created_at',)
    autocomplete_fields = ('user',)

    actions = ['approve_requests', 'reject_requests']

    @admin.action(description='Одобрить выбранные заявки')
    def approve_requests(self, request, queryset):
        count = 0
        for verification in queryset:
            verification.status = 'approved'
            verification.save()

            if verification.request_type == 'customer':
                verification.user.role = 'customer'
            elif verification.request_type == 'supplier':
                verification.user.role = 'supplier'

            verification.user.save()
            count += 1

        self.message_user(request, f'Одобрено заявок: {count}')

    @admin.action(description='Отклонить выбранные заявки')
    def reject_requests(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'Отклонено заявок: {updated}')
