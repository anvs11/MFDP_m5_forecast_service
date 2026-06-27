from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from models.user import User


class TransactionType:
    """Типы транзакций"""
    RECHARGE = "recharge"
    FORECAST = "forecast"
    REFUND = "refund"


class Transaction(SQLModel, table=True):
    """
    Запись об изменении баланса пользователя.
    Фиксирует пополнения и списания с описанием операции.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    tx_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        unique=True,
        index=True,
        description="Уникальный ID транзакции"
    )
    user_id: int = Field(
        foreign_key="user.id",
        index=True,
        description="ID пользователя"
    )
    amount: float = Field(
        ...,
        description="Сумма (положительная = пополнение, отрицательная = списание)"
    )
    tx_type: str = Field(
        ...,
        index=True,
        max_length=50,
        description="Тип транзакции (recharge, forecast, refund)"
    )
    description: str = Field(
        ...,
        max_length=500,
        description="Описание операции"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Время транзакции"
    )

    user: Optional["User"] = Relationship(
        back_populates="transactions",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def __str__(self) -> str:
        return f"Transaction(tx_id={self.tx_id}, amount={self.amount}, type={self.tx_type})"


class TransactionCreate(SQLModel):
    """DTO для создания транзакции"""
    user_id: int
    amount: float
    tx_type: str
    description: str


class TransactionResponse(SQLModel):
    """DTO для ответа с информацией о транзакции"""
    tx_id: str
    amount: float
    tx_type: str
    description: str
    timestamp: datetime
