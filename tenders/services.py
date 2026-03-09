from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from .models import Application, Lot, Tender


def close_expired_tenders():
    now = timezone.now()
    expired_tenders = Tender.objects.filter(
        status=Tender.STATUS_PUBLISHED,
        deadline__lte=now,
    ).prefetch_related(
        Prefetch("lots", queryset=Lot.objects.prefetch_related("applications"))
    )

    with transaction.atomic():
        for tender in expired_tenders:
            tender.status = Tender.STATUS_CLOSED
            tender.save(update_fields=["status", "updated_at"])

            for lot in tender.lots.all():
                if lot.winner_id:
                    continue

                winner_application = (
                    lot.applications.exclude(status=Application.STATUS_WITHDRAWN)
                    .order_by("price", "created_at")
                    .first()
                )

                if not winner_application:
                    continue

                lot.winner = winner_application.supplier
                lot.save(update_fields=["winner"])

                lot.applications.exclude(id=winner_application.id).update(status=Application.STATUS_LOST)
                winner_application.status = Application.STATUS_WINNER
                winner_application.save(update_fields=["status", "updated_at"])
