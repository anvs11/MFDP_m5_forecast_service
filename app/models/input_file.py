from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from models.forecast import Forecast


class FileType:
    """Типы загружаемых файлов"""
    SALES = "sales"
    CALENDAR = "calendar"
    PRICES = "prices"


class InputFile(SQLModel, table=True):
    """
    Модель загруженного CSV файла.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    forecast_id: int = Field(
        foreign_key="forecast.id",
        index=True,
        description="ID прогноза, к которому относится файл"
    )
    file_type: str = Field(
        ...,
        max_length=50,
        index=True,
        description="Тип файла (sales, calendar, prices)"
    )
    filename: str = Field(
        ...,
        max_length=255,
        description="Имя файла"
    )
    file_path: str = Field(
        ...,
        max_length=500,
        description="Путь к файлу в хранилище"
    )
    file_size: int = Field(
        ...,
        ge=0,
        description="Размер файла в байтах"
    )
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Время загрузки файла"
    )

    forecast: Optional["Forecast"] = Relationship(
        back_populates="input_files",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def __str__(self) -> str:
        return f"InputFile(id={self.id}, type={self.file_type}, filename={self.filename})"


class InputFileCreate(SQLModel):
    """DTO для создания записи о файле"""
    forecast_id: int
    file_type: str
    filename: str
    file_path: str
    file_size: int


class InputFileResponse(SQLModel):
    """DTO для ответа с информацией о файле"""
    id: int
    file_type: str
    filename: str
    file_size: int
    uploaded_at: datetime
