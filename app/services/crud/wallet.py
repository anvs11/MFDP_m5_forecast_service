from sqlmodel import Session, select
from typing import Optional
from models.wallet import Wallet
import logging

logger = logging.getLogger(__name__)


def get_wallet_by_user_id(user_id: int, session: Session) -> Optional[Wallet]:
    """Получить кошелек по ID пользователя"""
    statement = select(Wallet).where(Wallet.user_id == user_id)
    return session.exec(statement).first()


def create_wallet_for_user(user_id: int, session: Session, balance: float = 0.0) -> Wallet:
    """Создать кошелек для пользователя"""
    wallet = Wallet(user_id=user_id, balance=balance)
    session.add(wallet)
    return wallet


def update_balance(wallet: Wallet, amount: float, session: Session) -> Wallet:
    """Обновить баланс кошелька"""
    wallet.balance += amount
    session.add(wallet)
    return wallet