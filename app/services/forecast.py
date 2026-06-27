from sqlmodel import Session
import uuid
import json
from models.forecast import Forecast, ForecastCreate, TaskStatus
from models.ml_model import MLModel
from services.crud.forecast import create_forecast, update_forecast_status
from services.crud.ml_model import get_model_by_id
from services.balance import deduct_balance
from services.rm.rmq_client import rabbit_client
import logging

logger = logging.getLogger(__name__)


def create_forecast_task(
        user_id: int,
        model_id: str,
        store_id: str,
        dept_ids: list[str],
        horizon_days: int,
        alpha: float,
        session: Session
) -> Forecast:
    """
    Создать задачу прогноза.
    Автоматически списывает оплату и отправляет задачу в RabbitMQ.
    """
    # Получаем модель
    model = get_model_by_id(model_id, session)
    if not model:
        raise ValueError(f"Model '{model_id}' not found")

    if not model.is_active:
        raise ValueError(f"Model '{model_id}' is not active")

    # Создаем задачу прогноза
    forecast_data = ForecastCreate(
        user_id=user_id,
        model_id=model_id,
        store_id=store_id,
        dept_ids=json.dumps(dept_ids),
        horizon_days=horizon_days,
        alpha=alpha
    )

    forecast = create_forecast(forecast_data, session)

    # Рассчитываем стоимость (примерно: количество товаров × цена за товар)
    # В реальности нужно знать количество товаров в магазине/департаментах
    estimated_items = 614  # Примерно для CA_1 + FOODS_1/2
    total_cost = estimated_items * model.cost

    # Списываем оплату
    try:
        deduct_balance(user_id, total_cost, session)
        forecast.total_cost = total_cost
        session.add(forecast)
        session.commit()
    except ValueError as e:
        # Если недостаточно средств — отменяем задачу
        update_forecast_status(forecast.id, TaskStatus.FAILED, session, error=str(e))
        raise

    # Отправляем задачу в RabbitMQ
    try:
        rabbit_client.send_task(forecast)
        update_forecast_status(forecast.id, TaskStatus.PROCESSING, session)
        logger.info(f"Forecast task sent to RabbitMQ: id={forecast.id}")
    except Exception as e:
        logger.error(f"Failed to send forecast to RabbitMQ: {e}")
        update_forecast_status(forecast.id, TaskStatus.FAILED, session, error=f"RabbitMQ error: {str(e)}")
        raise

    return forecast
