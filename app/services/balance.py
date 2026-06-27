from sqlmodel import Session
from models.wallet import Wallet
from services.crud.transaction import create_transaction
from services.crud.wallet import get_wallet_by_user_id
import logging

logger = logging.getLogger(__name__)


def recharge_balance(user_id: int, amount: float, session: Session) -> None:
    """Пополнение баланса пользователя"""
    if amount <= 0:
        raise ValueError("Recharge amount must be positive")

    wallet = get_wallet_by_user_id(user_id, session)
    if not wallet:
        raise ValueError("Wallet not found")

    wallet.balance += amount
    session.add(wallet)

    create_transaction(
        user_id=user_id,
        amount=amount,
        tx_type="recharge",
        description=f"Recharged ${amount:.2f}",
        session=session
    )

    session.commit()
    logger.info(f"User {user_id} recharged ${amount:.2f}, new balance: ${wallet.balance:.2f}")


def deduct_balance(user_id: int, amount: float, session: Session) -> None:
    """Списание оплаты за операцию"""
    if amount <= 0:
        raise ValueError("Deduction amount must be positive")

    wallet = get_wallet_by_user_id(user_id, session)
    if not wallet:
        raise ValueError("Wallet not found")

    if wallet.balance < amount:
        raise ValueError(f"Insufficient balance. Current: ${wallet.balance:.2f}, required: ${amount:.2f}")

    wallet.balance -= amount
    session.add(wallet)

    create_transaction(
        user_id=user_id,
        amount=-amount,
        tx_type="forecast",
        description=f"Charged ${amount:.2f} for forecast",
        session=session
    )

    session.commit()
    logger.info(f"User {user_id} charged ${amount:.2f}, new balance: ${wallet.balance:.2f}")