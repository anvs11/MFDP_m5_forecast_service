from datetime import datetime, timedelta
import time
import logging
from fastapi import HTTPException, status
from jose import jwt, JWTError
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(email: str) -> str:
    """
    Создает JWT токен доступа для пользователя.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "exp": expire
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access token created for user: {email}")
    return token


def verify_access_token(token: str) -> dict:
    """
    Проверяет валидность JWT токена.
    """
    try:
        logger.debug(f"Attempting to decode token: {token[:20]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Decoded payload: {payload}")

        email = payload.get("sub")
        if email is None:
            logger.warning("Token has no subject")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no subject"
            )

        exp = payload.get("exp")
        if exp is None:
            logger.warning("Token has no expiration")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token has no expiration"
            )

        current_time = int(time.time())
        if current_time > exp:
            logger.warning("Token expired")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token expired"
            )

        logger.info(f"Token verified successfully for user: {email}")
        return payload

    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
