from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from config import get_settings
from database.database import init_db
from database.initdb import create_demo_data
from routes.auth import auth_router
from routes.user import user_router
from routes.forecast import forecast_router
from routes.health import health_router
from services.logging.logging import get_logger
import uvicorn

logger = get_logger(logger_name=__name__)
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_application() -> FastAPI:
    """
    Создаёт и настраивает FastAPI приложение
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.openapi_schema = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(forecast_router)

    return app


app = create_application()


@app.on_event("startup")
async def on_startup():
    try:
        logger.info("Инициализация базы данных...")
        await init_db()
        logger.info("Таблицы созданы успешно")

        logger.info("Создание демо-данных...")
        create_demo_data()

        logger.info("Приложение запущено успешно")
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Завершение работы приложения...")


if __name__ == '__main__':
    uvicorn.run(
        'api:app',
        host='0.0.0.0',
        port=8080,
        reload=True,
        log_level="info"
    )
