import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pika
import json
import logging
from sqlmodel import Session, create_engine
from config import get_settings
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from models.ml_model import MLModel
from models.forecast import Forecast, TaskStatus
from models.forecast_item import ForecastItem
from models.input_file import InputFile
from datetime import datetime

from model_config import (
    DATA_PATHS,
    MODEL_OUTPUT_PATH
)

from forecaster import run_forecast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

SALES_PATH = DATA_PATHS['sales']
CALENDAR_PATH = DATA_PATHS['calendar']
PRICES_PATH = DATA_PATHS['prices']

sync_engine = create_engine(
    f'postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}',
    echo=False,
    pool_pre_ping=True,
)


def callback(ch, method, properties, body):
    forecast_id = None
    try:
        message = json.loads(body)
        forecast_id = message['forecast_id']
        store_id = message['store_id']
        dept_ids = message['dept_ids']
        horizon_days = message['horizon_days']
        alpha = message['alpha']

        logger.info(f"Received forecast task: id={forecast_id}, store={store_id}")

        with Session(sync_engine) as session:
            forecast = session.get(Forecast, forecast_id)
            if not forecast:
                logger.error(f"Forecast {forecast_id} not found")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            forecast.status = TaskStatus.PROCESSING
            session.add(forecast)
            session.commit()

        logger.info(f"Running forecast for task {forecast_id}...")

        forecast_items = run_forecast(
            sales_path=SALES_PATH,
            calendar_path=CALENDAR_PATH,
            prices_path=PRICES_PATH,
            store_id=store_id,
            dept_ids=dept_ids,
            horizon_days=horizon_days,
            alpha=alpha,
            model_path=MODEL_OUTPUT_PATH
        )

        with Session(sync_engine) as session:
            forecast = session.get(Forecast, forecast_id)

            for item_data in forecast_items:
                forecast_item = ForecastItem(
                    forecast_id=forecast_id,
                    item_id=item_data['item_id'],
                    forecast_date=item_data['date'],
                    predicted_sales=item_data['predicted_sales'],
                    probability_of_sale=item_data['probability_of_sale'],
                    volume=item_data['volume']
                )
                session.add(forecast_item)

            forecast.status = TaskStatus.COMPLETED
            forecast.completed_at = datetime.utcnow()
            forecast.result = json.dumps({
                "total_items": len(forecast_items),
                "message": "Forecast completed successfully"
            })

            session.add(forecast)
            session.commit()

            logger.info(f"Forecast {forecast_id} completed: {len(forecast_items)} items")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Error processing forecast: {e}", exc_info=True)

        if forecast_id:
            try:
                with Session(sync_engine) as session:
                    forecast = session.get(Forecast, forecast_id)
                    if forecast:
                        forecast.status = TaskStatus.FAILED
                        forecast.error = str(e)
                        forecast.completed_at = datetime.utcnow()
                        session.add(forecast)
                        session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update forecast status: {db_error}")

        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    logger.info("ML Worker starting...")

    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue=settings.RABBITMQ_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=settings.RABBITMQ_QUEUE, on_message_callback=callback)

    logger.info(f"ML Worker started. Waiting for messages on queue: {settings.RABBITMQ_QUEUE}")
    logger.info(f"Model path: {MODEL_OUTPUT_PATH}")
    logger.info(f"Data paths: {DATA_PATHS}")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("ML Worker stopped by user")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
