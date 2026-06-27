from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date

if TYPE_CHECKING:
    from models.forecast import Forecast


class ForecastItem(SQLModel, table=True):
    """
    Результат прогноза для одного товара на одну дату.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    forecast_id: int = Field(
        foreign_key="forecast.id",
        index=True,
        description="ID прогноза"
    )
    item_id: str = Field(
        ...,
        max_length=100,
        index=True,
        description="ID товара (например, 'FOODS_1_001')"
    )
    forecast_date: date = Field(
        ...,
        description="Дата прогноза"
    )
    predicted_sales: float = Field(
        ...,
        ge=0,
        description="Предсказанные продажи"
    )
    probability_of_sale: float = Field(
        ...,
        ge=0,
        le=1,
        description="Вероятность продажи (из классификатора)"
    )
    volume: float = Field(
        ...,
        ge=0,
        description="Объем продаж (из регрессора)"
    )

    forecast: Optional["Forecast"] = Relationship(
        back_populates="forecast_items",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def __str__(self) -> str:
        return f"ForecastItem(item={self.item_id}, date={self.forecast_date}, sales={self.predicted_sales})"


class ForecastItemCreate(SQLModel):
    """DTO для создания результата прогноза"""
    forecast_id: int
    item_id: str
    forecast_date: date
    predicted_sales: float
    probability_of_sale: float
    volume: float


class ForecastItemResponse(SQLModel):
    """DTO для ответа с результатом прогноза"""
    item_id: str
    forecast_date: date
    predicted_sales: float
    probability_of_sale: float
    volume: float
