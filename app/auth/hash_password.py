from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class HashPassword:
    """
    Класс для хеширования и верификации паролей с использованием bcrypt.
    """

    @staticmethod
    def create_hash(password: str) -> str:
        """
        Создает хеш из переданного пароля.
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_hash(plain_password: str, hashed_password: str) -> bool:
        """
        Проверяет соответствие пароля его хешу.
        """
        return pwd_context.verify(plain_password, hashed_password)
