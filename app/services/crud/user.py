# app/services/crud/user.py
from sqlmodel import Session, select
from typing import Optional
from models.user import User, UserCreate
from auth.hash_password import HashPassword
import logging

logger = logging.getLogger(__name__)


def get_user_by_email(email: str, session: Session) -> Optional[User]:
    """Получить пользователя по email"""
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_user_by_id(user_id: int, session: Session) -> Optional[User]:
    """Получить пользователя по ID"""
    return session.get(User, user_id)


def get_all_users(session: Session) -> list[User]:
    """Получить всех пользователей"""
    statement = select(User)
    return session.exec(statement).all()


def create_user(user_data: UserCreate, session: Session) -> User:
    """
    Создать нового пользователя.
    ВАЖНО: кошелек создается отдельно через wallet.py!
    """
    # Проверяем уникальность email
    if get_user_by_email(user_data.email, session):
        raise ValueError("User with this email already exists")

    # Хэшируем пароль
    hasher = HashPassword()
    hashed_password = hasher.create_hash(user_data.password)

    # Создаем пользователя
    user = User(
        email=user_data.email,
        password=hashed_password,
        username=user_data.username
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"User created: {user.email} (id={user.id})")
    return user


def delete_user(user_id: int, session: Session) -> bool:
    """Удалить пользователя по ID"""
    user = get_user_by_id(user_id, session)
    if not user:
        return False

    session.delete(user)
    session.commit()
    logger.info(f"User deleted: id={user_id}")
    return True