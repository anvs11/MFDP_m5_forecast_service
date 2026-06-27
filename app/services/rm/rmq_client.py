import json
import pika
import logging
from typing import Optional
from models.forecast import Forecast, TaskStatus
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RabbitMQClient:
    """Клиент для взаимодействия с RabbitMQ."""

    def __init__(
            self,
            host: str = None,
            port: int = None,
            username: str = None,
            password: str = None,
            queue_name: str = None
    ):
        self.host = host or settings.RABBITMQ_HOST
        self.port = port or settings.RABBITMQ_PORT
        self.username = username or settings.RABBITMQ_USER
        self.password = password or settings.RABBITMQ_PASS
        self.queue_name = queue_name or settings.RABBITMQ_QUEUE

        self.connection_params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host='/',
            credentials=pika.PlainCredentials(
                username=self.username,
                password=self.password
            ),
            heartbeat=30,
            blocked_connection_timeout=2
        )

    def send_task(self, forecast: Forecast) -> bool:
        """
        Отправляет задачу прогноза в очередь RabbitMQ.

        Args:
            forecast: Объект Forecast для обработки

        Returns:
            bool: True если отправка прошла успешно
        """
        try:
            connection = pika.BlockingConnection(self.connection_params)
            channel = connection.channel()

            # Создаем очередь если её нет
            channel.queue_declare(queue=self.queue_name, durable=True)

            # Подготавливаем сообщение
            message = {
                "forecast_id": forecast.id,
                "store_id": forecast.store_id,
                "dept_ids": forecast.get_dept_ids_list(),
                "horizon_days": forecast.horizon_days,
                "alpha": forecast.alpha
            }

            # Отправляем сообщение
            channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # persistent
            )

            connection.close()
            logger.info(f"Forecast task sent to RabbitMQ: id={forecast.id}")
            return True

        except pika.exceptions.AMQPError as e:
            logger.error(f"RabbitMQ error: {str(e)}")
            return False


# Глобальный экземпляр клиента
rabbit_client = RabbitMQClient()