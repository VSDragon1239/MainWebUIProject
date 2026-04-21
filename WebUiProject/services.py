# WebUiProject/services.py
from django.db import transaction as db_transaction
from django.db.models import F
from .models import EcoWallet, EcoCoinTransaction


class InsufficientFundsError(Exception):
    pass


class EcoCoinService:
    @staticmethod
    def get_balance(user) -> int:
        """Быстрое получение баланса без блокировок (для отображения в UI)"""
        wallet = getattr(user, 'eco_wallet', None)
        if wallet:
            return wallet.balance
        return 0

    @staticmethod
    @db_transaction.atomic
    def process_transaction(user, amount: int, tx_type: str, external_id: str = None):
        amount = int(amount)
        if amount == 0:
            return

        # Блокируем строку кошелька в Postgres
        wallet, _ = EcoWallet.objects.select_for_update().get_or_create(
            user=user,
            defaults={'balance': 0}
        )

        if amount < 0 and wallet.balance < abs(amount):
            raise InsufficientFundsError("Недостаточно эко-коинов")

        # F() защищает от Race Conditions (конкурентных запросов)
        wallet.balance = F('balance') + amount
        wallet.save(update_fields=['balance'])

        EcoCoinTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            tx_type=tx_type,
            external_id=external_id
        )
        wallet.refresh_from_db(fields=['balance'])
        return wallet.balance

    @staticmethod
    def credit(user, amount: int, tx_type: str, external_id: str = None):
        return EcoCoinService.process_transaction(user, abs(amount), tx_type, external_id)

    @staticmethod
    def debit(user, amount: int, tx_type: str, external_id: str = None):
        return EcoCoinService.process_transaction(user, -abs(amount), tx_type, external_id)
