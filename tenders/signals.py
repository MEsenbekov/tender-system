from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import Tender


@receiver(post_save, sender=Tender)
def send_tender_result_notifications(sender, instance, created, **kwargs):
    if created:
        return

    if instance.status != 'closed':
        return

    if instance.notifications_sent:
        return

    if instance.customer.email:
        if instance.winner:
            customer_message = f"""
Тендер "{instance.title}" завершён.

Победитель: {instance.winner.username}
Дата завершения: {instance.created_at}

Вы можете просмотреть тендер в системе.
"""
        else:
            customer_message = f"""
Тендер "{instance.title}" завершён без выбора победителя.

Вы можете просмотреть тендер в системе.
"""

        send_mail(
            subject=f'Итоги тендера: {instance.title}',
            message=customer_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.customer.email],
            fail_silently=True,
        )

    # письма участникам
    for application in instance.applications.select_related('supplier'):
        if not application.supplier.email:
            continue

        if application.status == 'winner':
            app_message = f"""
Поздравляем!

По тендеру "{instance.title}" ваша заявка признана победившей.

Статус заявки: {application.status}
Предложенная цена: {application.price}
"""
        elif application.status == 'rejected':
            winner_name = instance.winner.username if instance.winner else 'не выбран'
            app_message = f"""
Тендер "{instance.title}" завершён.

Ваша заявка не победила.
Статус заявки: {application.status}
Победитель: {winner_name}
"""
        elif application.status == 'withdrawn':
            app_message = f"""
Тендер "{instance.title}" завершён.

Ваша заявка была ранее отозвана.
Статус заявки: {application.status}
"""
        else:
            winner_name = instance.winner.username if instance.winner else 'не выбран'
            app_message = f"""
Тендер "{instance.title}" завершён.

Статус вашей заявки: {application.status}
Победитель: {winner_name}
"""

        send_mail(
            subject=f'Итоги тендера: {instance.title}',
            message=app_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.supplier.email],
            fail_silently=True,
        )

    instance.notifications_sent = True
    Tender.objects.filter(pk=instance.pk).update(notifications_sent=True)
