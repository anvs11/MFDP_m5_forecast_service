from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session
from database.database import get_session
from models.user import User
from services.crud.wallet import get_wallet_by_user_id
from services.crud.transaction import get_transactions_by_user
from services.balance import recharge_balance
from dependencies.auth import get_current_user_universal
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/api/users", tags=["Users"])


class RechargeRequest(BaseModel):
    amount: float


class BalanceResponse(BaseModel):
    user_id: int
    balance: float


@user_router.get("/me")
def get_profile(
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    wallet = get_wallet_by_user_id(current_user.id, session)
    balance = wallet.balance if wallet else 0.0

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "balance": balance,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }


@user_router.get("/me/balance", response_model=BalanceResponse)
def get_balance(
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    wallet = get_wallet_by_user_id(current_user.id, session)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    return BalanceResponse(user_id=current_user.id, balance=wallet.balance)


@user_router.post("/me/recharge", response_model=BalanceResponse)
def recharge(
        request: RechargeRequest,
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    if request.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )

    try:
        recharge_balance(current_user.id, request.amount, session)
        session.commit()

        wallet = get_wallet_by_user_id(current_user.id, session)
        logger.info(f"User {current_user.email} recharged ${request.amount:.2f}")

        return BalanceResponse(user_id=current_user.id, balance=wallet.balance)

    except ValueError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Recharge failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recharge balance"
        )


@user_router.get("/me/transactions")
def get_transactions(
        current_user: User = Depends(get_current_user_universal),
        session: Session = Depends(get_session)
):
    transactions = get_transactions_by_user(current_user.id, session)

    return {
        "user_id": current_user.id,
        "transactions": [
            {
                "tx_id": tx.tx_id,
                "amount": tx.amount,
                "tx_type": tx.tx_type,
                "description": tx.description,
                "timestamp": tx.timestamp
            }
            for tx in transactions
        ]
    }
