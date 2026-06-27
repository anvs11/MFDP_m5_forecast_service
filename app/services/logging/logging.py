import logging
import os
from pathlib import Path


def get_logger(level=logging.INFO, logger_name='default_logger') -> logging.Logger:
    """
    Создает и настраивает логгер.
    """
    # Создаем директорию для логов
    log_dir = Path('./logs')
    log_dir.mkdir(exist_ok=True)

    # Базовая конфигурация
    logging.basicConfig(level=level)

    # Обработчик для файла
    handler = logging.FileHandler('./logs/app.log')

    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    # Получаем логгер
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger