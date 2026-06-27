from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import re

if TYPE_CHECKING:
    from models.wallet import Wallet
    from models.forecast import Forecast
    from models.transaction import Transaction


class UserBase(SQLModel):
    """
    Базовая модель пользователя с общими полями.
    """
    email: str = Field(
        ...,
        unique=True,
        index=True,
        min_length=5,
        max_length=255,
        description="Электронная почта пользователя"
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Хешированный пароль пользователя"
    )
    username: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Имя пользователя"
    )


class User(UserBase, table=True):
    """
    Модель пользователя для хранения в базе данных.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True, description="Активен ли аккаунт")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Дата создания аккаунта"
    )

    wallet: Optional["Wallet"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    forecasts: List["Forecast"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    transactions: List["Transaction"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._validate_email()
        self._validate_password()

    def _validate_email(self) -> None:
        """Проверяет корректность email"""
        email_pattern = re.compile(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$')
        if not email_pattern.match(self.email):
            raise ValueError("Invalid email format")

    def _validate_password(self) -> None:
        """Проверяет корректность пароля"""
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[^a-zA-Z0-9]', self.password):
            raise ValueError("Password must contain at least one special symbol")

    def __str__(self) -> str:
        return f"Id: {self.id}. Email: {self.email}"


class UserCreate(UserBase):
    """DTO для создания нового пользователя"""
    pass


class UserUpdate(SQLModel):
    """DTO для обновления пользователя"""
    username: Optional[str] = None
    is_active: Optional[bool] = None
