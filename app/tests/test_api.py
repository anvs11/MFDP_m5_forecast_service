"""Тесты API эндпоинтов"""
from fastapi.testclient import TestClient
from sqlmodel import Session


class TestHealthCheck:
    """Тесты health check"""

    def test_health_check(self, client: TestClient):
        """API должен отвечать на /health"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


class TestAuth:
    """Тесты авторизации и регистрации"""

    def test_register_user(self, client: TestClient):
        """Регистрация нового пользователя"""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "username": "newuser"
        }
        response = client.post("/auth/register", json=user_data)
        assert response.status_code in [200, 201]

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Регистрация с существующим email должна вернуть ошибку"""
        user_data = {
            "email": "test@example.com",
            "password": "password123",
            "username": "duplicate"
        }
        response = client.post("/auth/register", json=user_data)
        assert response.status_code in [400, 409]

    def test_register_short_password(self, client: TestClient):
        """Пароль должен быть не менее 8 символов"""
        user_data = {
            "email": "short@example.com",
            "password": "123",
            "username": "shortpass"
        }
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 422

    def test_login_success(self, client: TestClient, test_user):
        """Успешная авторизация"""
        response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Неправильный пароль"""
        response = client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 404]


class TestUserBalance:
    """Тесты баланса и транзакций"""

    def test_get_user_balance(self, authenticated_client: TestClient):
        """Получение баланса пользователя"""
        response = authenticated_client.get("/api/users/me/balance")
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert data["balance"] >= 0

    def test_get_user_profile(self, authenticated_client: TestClient):
        """Получение профиля пользователя"""
        response = authenticated_client.get("/api/users/me")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data

    def test_recharge_balance(self, authenticated_client: TestClient):
        """Пополнение баланса"""
        response = authenticated_client.post(
            "/api/users/me/recharge",
            json={"amount": 50.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["balance"] >= 150.0

    def test_recharge_negative_amount(self, authenticated_client: TestClient):
        """Пополнение на отрицательную сумму должно вернуть ошибку"""
        response = authenticated_client.post(
            "/api/users/me/recharge",
            json={"amount": -10.0}
        )
        assert response.status_code == 400

    def test_get_transactions(self, authenticated_client: TestClient):
        """Получение истории транзакций"""
        response = authenticated_client.get("/api/users/me/transactions")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data


class TestForecast:
    """Тесты прогнозов"""

    def test_get_forecast_history(self, authenticated_client: TestClient):
        """Получение истории прогнозов"""
        response = authenticated_client.get("/api/forecast/history")
        assert response.status_code == 200
        data = response.json()
        assert "forecasts" in data

    def test_create_forecast(self, authenticated_client: TestClient, session: Session):
        """Создание прогноза"""
        from models.forecast import Forecast

        forecast_data = {
            "model_id": "m5_hurdle_v1",
            "store_id": "CA_1",
            "dept_ids": ["FOODS_1"],
            "horizon_days": 28,
            "alpha": 0.2
        }
        response = authenticated_client.post("/api/forecast/run", json=forecast_data)

        # Прогноз может быть создан (200) или упасть при отправке в RabbitMQ (400)
        # В обоих случаях запись должна появиться в БД
        assert response.status_code in [200, 400]

        forecasts = session.query(Forecast).filter_by(user_id=1).all()
        assert len(forecasts) > 0

        forecast = forecasts[-1]
        assert forecast.store_id == "CA_1"
        assert forecast.model_id == "m5_hurdle_v1"
        assert forecast.horizon_days == 28
        assert forecast.alpha == 0.2


    def test_get_nonexistent_forecast(self, authenticated_client: TestClient):
        """Получение несуществующего прогноза"""
        response = authenticated_client.get("/api/forecast/99999")
        assert response.status_code == 404


class TestUnauthorized:
    """Тесты неавторизованного доступа"""

    def test_unauthorized_balance(self, client: TestClient):
        """Без токена нельзя получить баланс"""
        response = client.get("/api/users/me/balance")
        assert response.status_code in [401, 403]

    def test_unauthorized_forecast_history(self, client: TestClient):
        """Без токена нельзя получить историю прогнозов"""
        response = client.get("/api/forecast/history")
        assert response.status_code in [401, 403]
