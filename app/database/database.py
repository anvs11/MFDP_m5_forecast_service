from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Асинхронный engine (для FastAPI запросов)
async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Синхронный engine (для init_db, миграций, роутов)
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)


def get_session():
    """
    Генератор синхронной сессии для FastAPI роутов.
    Используется в Depends(get_session).
    """
    with Session(sync_engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


async def get_async_session() -> AsyncSession:
    """
    Зависимость FastAPI для получения асинхронной сессии.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db(drop_all: bool = False):
    """
    Инициализирует базу данных: создает таблицы.
    """
    try:
        async with async_engine.begin() as conn:
            if drop_all:
                logger.info("Удаление всех таблиц...")
                await conn.run_sync(SQLModel.metadata.drop_all)

            logger.info("Создание таблиц в базе данных...")
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Таблицы созданы успешно")

    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {str(e)}")
        raise
