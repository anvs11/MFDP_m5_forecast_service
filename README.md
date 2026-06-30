# M5 Forecast Service

Сервис прогнозирования спроса на скоропортящиеся товары на основе данных Kaggle M5 Competition.
Реализует Hurdle-модель (двухступенчатое прогнозирование) с микросервисной архитектурой, системой биллинга и веб-интерфейсом.

## Компоненты

| Сервис    | Порт        | Описание                          |
|-----------|-------------|-----------------------------------|
| webview   | 8501        | Streamlit веб-интерфейс           |
| app       | 8080        | FastAPI REST API                  |
| ml_worker | -           | ML воркер (обрабатывает прогнозы) |
| db        | 5432        | PostgreSQL                        |
| rabbitmq  | 5672, 15672 | Очередь задач                     |

## Быстрый старт

**Требования:** Docker Desktop, Docker Compose v2+, 8 GB RAM

```bash
git clone https://github.com/anvs11/MFDP_m5_forecast_service.git
cd MFDP_m5_forecast_service
docker-compose up -d
```

**Адреса после запуска:**

- Streamlit: http://localhost:8501
- Swagger API: http://localhost:8080/docs
- RabbitMQ UI: http://localhost:15672 (guest/guest)

**Демо-доступ:**

- Email: `admin@m5forecast.com`
- Пароль: `admin123`
- Начальный баланс: $100

## Использование

### Создание прогноза

1. Войдите в систему
2. Перейдите на вкладку **"Создать прогноз"**
3. Выберите параметры:
   - Магазин: CA_1, CA_2, CA_3 или CA_4
   - Департаменты: FOODS_1, FOODS_2
   - Горизонт: 7–28 дней
   - Alpha: 0.05–0.50 (квантиль)
4. Дождитесь обработки (10–30 секунд)

### Основные возможности

- **Результаты** — таблица прогнозов, графики "Топ-20" и распределения рисков, экспорт CSV/PNG
- **Сценарии** — сравнение Baseline (0.5), Balanced (0.35), Optimal (0.2) и пользовательского варианта
- **Сравнение магазинов** — параллельный запуск прогнозов для 2–4 магазинов
- **Личный кабинет** — баланс, пополнение, история транзакций

## REST API

Полная документация: http://localhost:8080/docs

### Health check

| Метод | Эндпоинт    | Описание                                       |
|-------|-------------|------------------------------------------------|
| GET   | `/health`   | Health check endpoint для Docker и мониторинга |

### Аутентификация

| Метод | Эндпоинт         | Описание                          |
|-------|------------------|-----------------------------------|
| POST  | `/auth/register` | Регистрация                       |
| POST  | `/auth/login`    | Авторизация (JWT)                 |
| GET   | `/auth/logout`   | Выход из системы (удаляет cookie) |

### Пользователи

| Метод  | Эндпоинт                     | Описание   |
|--------|------------------------------|------------|
| GET    | `/api/users/me`              | Профиль    |
| GET    | `/api/users/me/balance`      | Баланс     |
| POST   | `/api/users/me/recharge`     | Пополнение |
| GET    | `/api/users/me/transactions` | Транзакции |

### Прогнозы

| Метод  | Эндпоинт                                  | Описание        |
|--------|-------------------------------------------|-----------------|
| POST   | `/api/forecast/run`                       | Создать прогноз |
| GET    | `/api/forecast/history`                   | История         |
| GET    | `/api/forecast/{forecast_id}`             | Статус          |
| GET    | `/api/forecast/{forecast_id}/summary`     | Результаты      |
| GET    | `/api/forecast/{forecast_id}/scenarios`   | Сценарии        |
| GET    | `/api/forecast/{forecast_id}/download`    | Скачать CSV     |

## Тестирование

Проект покрыт **22 тестами** (pytest).

```bash
# Запуск всех тестов
docker-compose exec app pytest tests/ -v

# С отчётом о покрытии
docker-compose exec app pytest tests/ --cov=. --cov-report=term-missing
```

**Структура тестов:**

- `test_api.py` — 16 тестов API (auth, balance, forecast, unauthorized)
- `test_db.py` — 6 тестов моделей БД (User, Wallet, Forecast)

## Масштабирование

```bash
# Запустить 3 воркера
docker-compose up -d --scale ml_worker=3

# Вернуться к 1 воркеру
docker-compose up -d --scale ml_worker=1
```

RabbitMQ распределяет задачи по воркерам (Round-Robin), каждый воркер обрабатывает 1 задачу за раз (`prefetch_count=1`). При сравнении 4 магазинов с 3 воркерами время выполнения сокращается примерно в 3 раза.

## ML Модель

**Hurdle Model** (двухступенчатое прогнозирование):

1. **LightGBM Classifier** — вероятность продажи товара
2. **LightGBM Regressor** — объём продаж при условии продажи

**Признаки:** `lag_7/14/21/28`, `rolling_mean_7`, `rolling_std_7`, `price_bin`, `demand_level`, `snap_*`, взаимодействия признаков и события.

**Квантили:**

| Alpha   | Сценарий  | Описание                                         |
|---------|-----------|--------------------------------------------------|
| 0.5     | Baseline  | Стандартный прогноз                              |
| 0.35    | Balanced  | Сбалансированный                                 |
| 0.2     | Optimal   | Оптимальный для скоропорта, снижение потерь ~17% |

## Технологии

- **Backend:** FastAPI 0.115, SQLModel 0.0.22, PostgreSQL 15, RabbitMQ 3.12, Pika 1.3.2, Passlib+bcrypt, python-jose (JWT)
- **ML:** LightGBM 4.5.0, scikit-learn 1.5.2, pandas 2.2.3, numpy 2.1.3
- **Frontend:** Streamlit 1.31, Plotly 5.18, Requests 2.31
- **Инфраструктура:** Docker, Docker Compose, pytest 8.3.3
