"""Тесты работы с БД"""
from sqlmodel import Session
from models.user import User
from models.wallet import Wallet
from models.forecast import Forecast, TaskStatus
from auth.hash_password import HashPassword


class TestUserModel:
    """Тесты модели User"""

    def test_create_user(self, session: Session):
        """Создание пользователя"""
        user = User(
            email="db_test@example.com",
            username="dbtest",
            password=HashPassword.create_hash("password123")
        )
        session.add(user)
        session.commit()

        retrieved_user = session.get(User, user.id)
        assert retrieved_user is not None
        assert retrieved_user.email == "db_test@example.com"

    def test_delete_user(self, session: Session):
        """Удаление пользователя"""
        user = User(
            email="delete_test@example.com",
            username="deletetest",
            password=HashPassword.create_hash("password123")
        )
        session.add(user)
        session.commit()

        user_id = user.id
        session.delete(user)
        session.commit()

        deleted_user = session.get(User, user_id)
        assert deleted_user is None


class TestWalletModel:
    """Тесты модели Wallet"""

    def test_create_wallet(self, session: Session):
        """Создание кошелька"""
        user = User(
            email="wallet_test@example.com",
            username="wallettest",
            password=HashPassword.create_hash("password123")
        )
        session.add(user)
        session.commit()

        wallet = Wallet(user_id=user.id, balance=100.0)
        session.add(wallet)
        session.commit()

        retrieved_wallet = session.get(Wallet, wallet.id)
        assert retrieved_wallet is not None
        assert retrieved_wallet.balance == 100.0

    def test_update_balance(self, session: Session):
        """Обновление баланса"""
        user = User(
            email="balance_test@example.com",
            username="balancetest",
            password=HashPassword.create_hash("password123")
        )
        session.add(user)
        session.commit()

        wallet = Wallet(user_id=user.id, balance=100.0)
        session.add(wallet)
        session.commit()

        wallet.balance += 50.0
        session.add(wallet)
        session.commit()

        updated_wallet = session.get(Wallet, wallet.id)
        assert updated_wallet.balance == 150.0


class TestForecastModel:
    """Тесты модели Forecast"""

    def test_create_forecast(self, session: Session):
        """Создание прогноза"""
        user = User(
            email="forecast_test@example.com",
            username="forecasttest",
            password=HashPassword.create_hash("password123")
        )
        session.add(user)
        session.commit()

        forecast = Forecast(
            user_id=user.id,
            model_id="m5_hurdle_v1",
            store_id="CA_1",
            dept_ids='["FOODS_1"]',
            horizon_days=28,
            alpha=0.2,
            status=TaskStatus.PENDING
        )
        session.add(forecast)
        session.commit()

        retrieved_forecast = session.get(Forecast, forecast.id)
        assert retrieved_forecast is not None
        assert retrieved_forecast.store_id == "CA_1"

    def test_update_forecast_status(self, session: Session):
        """Обновление статуса прогноза"""
        user = User(
            email="status_test@example.com",
            username="statustest",
            password=HashPassword.create_hash("password123")
        )
        session.add(user)
        session.commit()

        forecast = Forecast(
            user_id=user.id,
            model_id="m5_hurdle_v1",
            store_id="CA_1",
            dept_ids='["FOODS_1"]',
            horizon_days=28,
            alpha=0.2,
            status=TaskStatus.PENDING
        )
        session.add(forecast)
        session.commit()

        forecast.status = TaskStatus.COMPLETED
        session.add(forecast)
        session.commit()

        updated_forecast = session.get(Forecast, forecast.id)
        assert updated_forecast.status == TaskStatus.COMPLETED
