from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User


class Wallet(SQLModel, table=True):
    """
    Кошелек пользователя для управления балансом.
    Каждый пользователь имеет ровно один кошелек.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        foreign_key="user.id",
        unique=True,
        index=True,
        description="ID пользователя"
    )
    balance: float = Field(
        default=0.0,
        ge=0,
        description="Баланс кошелька (не может быть отрицательным)"
    )

    user: Optional["User"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def __str__(self) -> str:
        return f"Wallet(user_id={self.user_id}, balance={self.balance})"


class WalletCreate(SQLModel):
    """DTO для создания кошелька"""
    user_id: int
    balance: float = 0.0


class WalletUpdate(SQLModel):
    """DTO для обновления кошелька"""
    balance: Optional[float] = None
