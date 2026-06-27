from sqlmodel import Session, select
from typing import Optional, List
from models.forecast import Forecast, ForecastCreate, TaskStatus
from models.input_file import InputFile, InputFileCreate
from models.forecast_item import ForecastItem, ForecastItemCreate
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def create_forecast(forecast_data: ForecastCreate, session: Session) -> Forecast:
    """Создать новую задачу прогноза"""
    forecast = Forecast(
        user_id=forecast_data.user_id,
        model_id=forecast_data.model_id,
        store_id=forecast_data.store_id,
        dept_ids=forecast_data.dept_ids,
        horizon_days=forecast_data.horizon_days,
        alpha=forecast_data.alpha,
        status=TaskStatus.PENDING
    )
    session.add(forecast)
    session.commit()
    session.refresh(forecast)
    logger.info(f"Forecast created: id={forecast.id}, user={forecast.user_id}")
    return forecast


def get_forecast_by_id(forecast_id: int, session: Session) -> Optional[Forecast]:
    """Получить прогноз по ID"""
    return session.get(Forecast, forecast_id)


def get_forecasts_by_user(user_id: int, session: Session) -> List[Forecast]:
    """Получить все прогнозы пользователя"""
    statement = (
        select(Forecast)
        .where(Forecast.user_id == user_id)
        .order_by(Forecast.created_at.desc())
    )
    return session.exec(statement).all()


def update_forecast_status(
        forecast_id: int,
        status: TaskStatus,
        session: Session,
        result: Optional[str] = None,
        error: Optional[str] = None
) -> Optional[Forecast]:
    """Обновить статус прогноза"""
    forecast = get_forecast_by_id(forecast_id, session)
    if not forecast:
        return None

    forecast.status = status
    if result:
        forecast.result = result
    if error:
        forecast.error = error
    if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        forecast.completed_at = datetime.utcnow()

    session.add(forecast)
    session.commit()
    session.refresh(forecast)
    return forecast


def add_input_file(file_data: InputFileCreate, session: Session) -> InputFile:
    """Добавить информацию о загруженном файле"""
    input_file = InputFile(
        forecast_id=file_data.forecast_id,
        file_type=file_data.file_type,
        filename=file_data.filename,
        file_path=file_data.file_path,
        file_size=file_data.file_size
    )
    session.add(input_file)
    session.commit()
    session.refresh(input_file)
    return input_file


def create_forecast_items(items: List[ForecastItemCreate], session: Session) -> List[ForecastItem]:
    """Создать результаты прогноза (массово)"""
    forecast_items = [
        ForecastItem(
            forecast_id=item.forecast_id,
            item_id=item.item_id,
            date=item.date,
            predicted_sales=item.predicted_sales,
            probability_of_sale=item.probability_of_sale,
            volume=item.volume
        )
        for item in items
    ]
    session.add_all(forecast_items)
    session.commit()
    logger.info(f"Created {len(forecast_items)} forecast items")
    return forecast_items


def get_forecast_items(forecast_id: int, session: Session) -> List[ForecastItem]:
    """Получить все результаты прогноза"""
    statement = select(ForecastItem).where(ForecastItem.forecast_id == forecast_id)
    return session.exec(statement).all()