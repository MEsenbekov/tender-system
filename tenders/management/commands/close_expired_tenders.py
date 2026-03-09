from django.core.management.base import BaseCommand

from tenders.services import close_expired_tenders


class Command(BaseCommand):
    help = "Закрывает просроченные тендеры и выбирает победителей по минимальной цене, если они ещё не выбраны."

    def handle(self, *args, **options):
        close_expired_tenders()
        self.stdout.write(self.style.SUCCESS("Просроченные тендеры обработаны."))