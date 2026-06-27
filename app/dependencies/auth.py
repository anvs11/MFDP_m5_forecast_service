import asyncio
import json
from fastapi import Depends, HTTPException, status, Request
from sqlmodel import Session
from database.database import get_session
from auth.jwt_handler import verify_access_token
from services.crud.user import get_user_by_email
from models.user import User
from auth.hash_password import HashPassword
import logging

logger = logging.getLogger(__name__)


async def get_current_user_universal(
        request: Request,
        session: Session = Depends(get_session)
) -> User:
    """
    Универсальная функция аутентификации.
    """
    token = None

    # 1. Пробуем cookie
    token = request.cookies.get("access_token")
    if token:
        # Убираем кавычки, если есть
        if token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        # Убираем "Bearer ", если есть
        if token.startswith("Bearer "):
            token = token[7:]
    else:
        # 2. Пробуем заголовок Authorization
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
        else:
            # 3. Пробуем тело запроса как JSON (для бота)
            try:
                body = await request.body()
                if body:
                    data = json.loads(body.decode())
                    email = data.get("email")
                    password = data.get("password")
                    if email and password:
                        user = get_user_by_email(email, session)
                        if user:
                            hasher = HashPassword()
                            if hasher.verify_hash(password, user.password):
                                return user
            except:
                pass

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        payload = verify_access_token(token)
        email = payload["sub"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = get_user_by_email(email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
