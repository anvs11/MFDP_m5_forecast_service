from sqlmodel import Session, select
from database.database import sync_engine
from models.user import User
from models.wallet import Wallet
from models.ml_model import MLModel
from models.transaction import Transaction
from auth.hash_password import HashPassword
from config import get_settings
import logging
import uuid

logger = logging.getLogger(__name__)


def create_demo_data():
    """
    Создает демо-данные в базе данных:
    - Демо-пользователи с кошельками
    - ML модель для прогнозирования
    """
    try:
        with Session(sync_engine) as session:
            if session.exec(select(User)).first() is not None:
                logger.info("Пользователи уже существуют, пропускаем создание демо-данных")
                return

            logger.info("Создание демо-данных...")
            hasher = HashPassword()
            settings = get_settings()

            demo_users = [
                User(
                    email="admin@m5forecast.com",
                    password=hasher.create_hash("admin123"),
                    username="admin"
                ),
                User(
                    email="manager@m5forecast.com",
                    password=hasher.create_hash("manager123"),
                    username="manager"
                ),
            ]

            for user in demo_users:
                session.add(user)

            session.commit()
            logger.info(f"Создано {len(demo_users)} демо-пользователей")

            for user in demo_users:
                fresh_user = session.exec(
                    select(User).where(User.email == user.email)
                ).first()

                wallet = Wallet(user_id=fresh_user.id, balance=settings.DEMO_BALANCE)
                session.add(wallet)

                transaction = Transaction(
                    tx_id=str(uuid.uuid4()),
                    user_id=fresh_user.id,
                    amount=settings.DEMO_BALANCE,
                    tx_type="recharge",
                    description=f"Demo balance at registration",
                )
                session.add(transaction)

            session.commit()
            logger.info(f"Создано {len(demo_users)} кошельков с балансом ${settings.DEMO_BALANCE}")
            logger.info(f"Создано {len(demo_users)} транзакций начисления демо-баланса")

            m5_model = MLModel(
                model_id="m5_hurdle_v1",
                name="M5 Hurdle Model",
                cost=0.01,
                alpha=0.2,
                horizon_days=28,
                description="Двухэтапная модель (Hurdle) для прогнозирования спроса на скоропортящиеся товары. "
                            "Классификатор определяет вероятность продажи, регрессор предсказывает объем."
            )

            session.add(m5_model)
            session.commit()
            logger.info(f"Создана ML модель: {m5_model.model_id} (cost=${m5_model.cost} за товар)")

    except Exception as e:
        logger.error(f"Ошибка создания демо-данных: {str(e)}")
        raise
