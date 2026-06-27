from sqlmodel import Session, select
from typing import Optional
from models.transaction import Transaction, TransactionCreate
import uuid
import logging

logger = logging.getLogger(__name__)


def create_transaction(
    user_id: int,
    amount: float,
    tx_type: str,
    description: str,
    session: Session
) -> Transaction:
    """Создать транзакцию"""
    tx = Transaction(
        tx_id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,
        tx_type=tx_type,
        description=description
    )
    session.add(tx)
    return tx


def get_transactions_by_user(user_id: int, session: Session) -> list[Transaction]:
    """Получить все транзакции пользователя"""
    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
    )
    return session.exec(statement).all()