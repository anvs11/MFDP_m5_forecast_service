from fastapi import (APIRouter, HTTPException, status, Depends, Response)
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from database.database import get_session
from services.crud.user import create_user, get_user_by_email
from services.crud.wallet import create_wallet_for_user
from services.balance import recharge_balance
from models.user import User, UserCreate
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from dependencies.auth import get_current_user_universal
from config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
        user_data: UserCreate,
        response: Response,
        session: Session = Depends(get_session)
):
    """
    Регистрация нового пользователя.
    Автоматически создает кошелек и начисляет $100 демо-кредитов.
    """
    try:
        user = create_user(user_data, session)

        create_wallet_for_user(user.id, session, balance=0.0)

        recharge_balance(user.id, settings.DEMO_BALANCE, session)

        session.commit()
        session.refresh(user)

        logger.info(f"User registered: {user.email} (id={user.id})")

        # автоматически логиним пользователя (устанавливаем cookie)
        access_token = create_access_token(user.email)
        response.set_cookie(
            key=settings.COOKIE_NAME,
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=False,
            samesite="lax"
        )

        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "email": user.email,
            "demo_balance": settings.DEMO_BALANCE,
            "access_token": access_token
        }

    except ValueError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@auth_router.post("/login")
def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: Session = Depends(get_session)
):
    """
    Аутентификация пользователя.
    Возвращает JWT токен и устанавливает cookie.
    """
    user = get_user_by_email(form_data.username, session)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    hasher = HashPassword()
    if not hasher.verify_hash(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = create_access_token(user.email)

    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=False,
        samesite="lax"
    )

    logger.info(f"User logged in: {user.email}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email
    }


@auth_router.get("/logout")
def logout(response: Response):
    """
    Выход из системы.
    Удаляет cookie с токеном.
    """
    response.delete_cookie(settings.COOKIE_NAME)
    return {"message": "Logged out successfully"}
