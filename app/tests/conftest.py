import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from api import app
from database.database import get_session
from dependencies.auth import get_current_user_universal
from models.user import User
from auth.hash_password import HashPassword


@pytest.fixture(name="session")
def session_fixture():
    """Тестовая БД в SQLite (in-memory)"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Тестовый клиент без авторизации"""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(session: Session):
    """Тестовый клиент с авторизованным пользователем"""
    from models.wallet import Wallet
    from models.ml_model import MLModel

    def get_session_override():
        return session

    def get_current_user_override():
        # Создаем пользователя
        user = User(
            email="test@example.com",
            username="testuser",
            password=HashPassword.create_hash("testpassword123"),
            is_active=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # Создаем кошелек для пользователя
        wallet = Wallet(user_id=user.id, balance=100.0)
        session.add(wallet)

        # Создаем ML модель для тестов
        ml_model = MLModel(
            model_id="m5_hurdle_v1",
            name="M5 Hurdle Model v1",
            cost=6.14,
            alpha=0.2,
            horizon_days=28,
            description="Test model",
            is_active=True
        )
        session.add(ml_model)
        session.commit()

        return user

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user_universal] = get_current_user_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Создаёт тестового пользователя в БД"""
    user = User(
        email="test@example.com",
        username="testuser",
        password=HashPassword.create_hash("testpassword123"),
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
