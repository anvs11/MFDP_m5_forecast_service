from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.forecast import Forecast


class MLModelBase(SQLModel):
    """
    Базовая модель ML модели.
    """
    model_config = {"protected_namespaces": ()}
    model_id: str = Field(
        ...,
        unique=True,
        index=True,
        max_length=100,
        description="Уникальный идентификатор модели"
    )
    name: str = Field(
        ...,
        max_length=200,
        description="Название модели"
    )
    cost: float = Field(
        ...,
        gt=0,
        description="Стоимость прогноза за 1 товар (в долларах)"
    )
    alpha: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Квантиль для регрессора (0.0-1.0)"
    )
    horizon_days: int = Field(
        default=28,
        gt=0,
        description="Горизонт прогноза в днях"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Описание модели"
    )


class MLModel(MLModelBase, table=True):
    """
    Модель ML модели для хранения в базе данных.
    """
    model_config = {"protected_namespaces": ()}
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True, description="Активна ли модель")

    # Связи
    forecasts: List["Forecast"] = Relationship(
        back_populates="ml_model",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def __str__(self) -> str:
        return f"MLModel(id={self.model_id}, name={self.name}, cost={self.cost})"


class MLModelCreate(MLModelBase):
    """DTO для создания ML модели"""
    model_config = {"protected_namespaces": ()}
    pass


class MLModelUpdate(SQLModel):
    """DTO для обновления ML модели"""
    name: Optional[str] = None
    cost: Optional[float] = None
    alpha: Optional[float] = None
    horizon_days: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
