```text
app/
├── auth/                          # Аутентификация (как у куратора)
│   ├── __init__.py
│   ├── jwt_handler.py             # JWT создание/верификация
│   ├── hash_password.py           # Хэширование паролей
│   └── authenticate.py            # Проверка токенов
│
├── security/                      # Безопасность (из твоего проекта)
│   ├── __init__.py
│   └── cookie_auth.py             # OAuth2 с cookie
│
├── dependencies/                  # Зависимости FastAPI
│   ├── __init__.py
│   └── auth.py                    # get_current_user()
│
├── database/                      # База данных
│   ├── __init__.py
│   ├── config.py                  # Настройки БД
│   ├── database.py                # Подключение к PostgreSQL
│   └── initdb.py                  # Инициализация таблиц
│
├── models/                        # SQLAlchemy модели
│   ├── __init__.py
│   ├── user.py                    # User модель
│   ├── forecast.py                # Forecast модель
│   ├── input_file.py              # InputFile модель
│   └── forecast_item.py           # ForecastItem модель
│
├── schemas/                       # Pydantic схемы (для API)
│   ├── __init__.py
│   ├── user.py                    # UserCreate, UserResponse
│   └── forecast.py                # Forecast schemas
│
├── services/
│   └── crud/                      # CRUD операции
│       ├── __init__.py
│       ├── user.py                # get_user_by_email(), create_user()
│       └── forecast.py            # forecast CRUD
│
├── routes/                        # API эндпоинты
│   ├── __init__.py
│   ├── auth.py                    # /auth/login, /auth/register
│   ├── forecast.py                # /api/forecast/*
│   └── user.py                    # /api/users/*
│
├── services/
│   └── rmq/                       # RabbitMQ интеграция
│       ├── __init__.py
│       └── rmq_client.py          # Отправка задач в очередь
│
├── logs/                          # Логи (создастся автоматически)
│
├── tests/                         # Тесты
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_forecast.py
│
├── api.py                         # Точка входа FastAPI
├── config.py                      # Общие настройки
├── Dockerfile
└── requirements.txt
```