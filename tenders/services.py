from django.utils import timezone
from .models import Tender


def close_expired_tenders():
    expired = Tender.objects.filter(
        status='published',
        deadline__lte=timezone.now()
    )
    expired.update(status='closed')
