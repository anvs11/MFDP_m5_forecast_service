# Доменная модель сервиса M5 Forecast Service

## Описание
Сервис для прогнозирования спроса на скоропортящиеся товары на основе 
ML-модели (Hurdle Model). Пользователь загружает 3 CSV-файла, 
настраивает параметры и получает прогноз продаж.

## Ключевые сущности

### 1. User (Пользователь)
Менеджер по закупкам, который работает с сервисом.

**Атрибуты:**
- `id` (UUID) — уникальный идентификатор
- `username` (string) — логин
- `email` (string) — email
- `password_hash` (string) — хэш пароля (bcrypt)
- `created_at` (datetime) — дата регистрации
- `is_active` (bool) — активен ли аккаунт

### 2. Forecast (Прогноз)
Задача на расчет прогноза. Один пользователь может создавать много прогнозов.

**Атрибуты:**
- `id` (UUID) — уникальный идентификатор
- `user_id` (UUID, FK → User) — владелец
- `name` (string) — название прогноза (например, "Прогноз на май 2026")
- `status` (enum) — статус: `pending`, `processing`, `completed`, `failed`
- `alpha` (float) — квантиль для регрессора (0.14–0.5)
- `store_id` (string) — магазин (например, "CA_1")
- `dept_ids` (list[string]) — департаменты (например, ["FOODS_1", "FOODS_2"])
- `created_at` (datetime) — дата создания
- `completed_at` (datetime) — дата завершения
- `error_message` (string, nullable) — сообщение об ошибке
- `metrics` (JSON, nullable) — метрики качества (MAE, SCL, Fill Rate)

### 3. InputFile (Загруженный файл)
CSV-файл, который пользователь загрузил для прогноза.

**Атрибуты:**
- `id` (UUID) — уникальный идентификатор
- `forecast_id` (UUID, FK → Forecast) — к какому прогнозу относится
- `file_type` (enum) — тип: `sales`, `calendar`, `prices`
- `filename` (string) — имя файла
- `file_path` (string) — путь к файлу в хранилище
- `file_size` (int) — размер в байтах
- `uploaded_at` (datetime) — дата загрузки

### 4. ForecastItem (Строка прогноза)
Результат прогноза для одного товара на одну дату.

**Атрибуты:**
- `id` (UUID) — уникальный идентификатор
- `forecast_id` (UUID, FK → Forecast) — к какому прогнозу относится
- `item_id` (string) — ID товара (например, "FOODS_1_001")
- `date` (date) — дата прогноза
- `predicted_sales` (float) — предсказанные продажи
- `probability_of_sale` (float) — вероятность продажи (из классификатора)
- `volume` (float) — объем продаж (из регрессора)

## Бизнес-процесс
1. Пользователь регистрируется - создается User;
2. Пользователь загружает 3 CSV - создаются 3 InputFile + Forecast (status=pending);
3. Пользователь нажимает "Запустить прогноз" - Forecast переходит в status=processing;
4. ML-воркер обрабатывает задачу - создает ForecastItem для каждого товара/даты;
5. После завершения - Forecast переходит в status=completed, заполняются metrics;
6. Пользователь может скачать результат как CSV
