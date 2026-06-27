from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
import json

if TYPE_CHECKING:
    from models.user import User
    from models.ml_model import MLModel
    from models.input_file import InputFile
    from models.forecast_item import ForecastItem


class TaskStatus(str, Enum):
    """Статусы выполнения задачи прогноза"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ForecastBase(SQLModel):
    """
    Базовая модель задачи прогноза.
    """
    store_id: str = Field(
        ...,
        max_length=50,
        description="ID магазина (например, 'CA_1')"
    )
    dept_ids: str = Field(
        ...,
        description="Список департаментов в формате JSON (например, '[\"FOODS_1\", \"FOODS_2\"]')"
    )
    horizon_days: int = Field(
        default=28,
        gt=0,
        description="Горизонт прогноза в днях"
    )
    alpha: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Квантиль для регрессора"
    )


class Forecast(ForecastBase, table=True):
    """
    Модель задачи прогноза для хранения в базе данных.
    """
    model_config = {"protected_namespaces": ()}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        foreign_key="user.id",
        index=True,
        description="ID пользователя, создавшего прогноз"
    )
    model_id: str = Field(
        foreign_key="mlmodel.model_id",
        index=True,
        description="ID использованной ML модели"
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Статус задачи"
    )
    total_cost: float = Field(
        default=0.0,
        ge=0,
        description="Итоговая стоимость прогноза"
    )
    result: Optional[str] = Field(
        default=None,
        description="JSON с метриками (MAE, SCL, Fill Rate)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Сообщение об ошибке"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Время создания задачи"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Время завершения задачи"
    )

    user: Optional["User"] = Relationship(
        back_populates="forecasts",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    ml_model: Optional["MLModel"] = Relationship(
        back_populates="forecasts",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    input_files: List["InputFile"] = Relationship(
        back_populates="forecast",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    forecast_items: List["ForecastItem"] = Relationship(
        back_populates="forecast",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def get_dept_ids_list(self) -> List[str]:
        """Возвращает список департаментов"""
        try:
            return json.loads(self.dept_ids)
        except:
            return []

    def get_result_dict(self) -> Optional[dict]:
        """Возвращает результат как словарь"""
        if self.result:
            try:
                return json.loads(self.result)
            except:
                return None
        return None

    def __str__(self) -> str:
        return f"Forecast(id={self.id}, status={self.status}, store={self.store_id})"


class ForecastCreate(ForecastBase):
    """DTO для создания задачи прогноза"""
    model_config = {"protected_namespaces": ()}
    user_id: int
    model_id: str
    store_id: str
    dept_ids: str
    horizon_days: int = 28
    alpha: float = 0.2


class ForecastUpdate(SQLModel):
    """DTO для обновления задачи прогноза"""
    status: Optional[TaskStatus] = None
    total_cost: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


class ForecastResponse(SQLModel):
    """DTO для ответа с информацией о прогнозе"""
    model_config = {"protected_namespaces": ()}
    id: int
    user_id: int
    model_id: str
    store_id: str
    dept_ids: str
    horizon_days: int
    alpha: float
    status: TaskStatus
    total_cost: float
    result: Optional[str]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
