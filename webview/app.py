import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import time

API_BASE_URL = "http://app:8080"


# ==================== КЭШИРОВАНИЕ ====================

@st.cache_data(ttl=300)
def get_forecasts_cached():
    """Получить список прогнозов (кэшируется)"""
    response = requests.get(
        f"{API_BASE_URL}/api/forecast/history",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return None


@st.cache_data(ttl=60)
def get_forecast_status_cached(forecast_id: int):
    response = requests.get(
        f"{API_BASE_URL}/api/forecast/{forecast_id}",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return None


@st.cache_data(ttl=600)
def get_forecast_summary_cached(forecast_id: int):
    response = requests.get(
        f"{API_BASE_URL}/api/forecast/{forecast_id}/summary",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return None


def get_forecasts():
    return get_forecasts_cached()


def get_forecast_status(forecast_id: int):
    return get_forecast_status_cached(forecast_id)


def get_forecast_summary(forecast_id: int):
    return get_forecast_summary_cached(forecast_id)


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None


# ==================== ФУНКЦИИ API ====================

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def login(email: str, password: str) -> dict:
    """Авторизация через API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            data={"username": email, "password": password}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Неверный email или пароль"}
    except requests.exceptions.ConnectionError:
        return {"error": "Не удалось подключиться к серверу"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}


def register(username: str, email: str, password: str) -> dict:
    """Регистрация нового пользователя"""
    payload = {
        "email": email,
        "password": password,
        "username": username or email.split('@')[0]
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json=payload
        )
        # ✅ ИСПРАВЛЕНО: принимаем и 200, и 201
        if response.status_code in [200, 201]:
            result = response.json()
            # Если нет access_token, логинимся отдельно
            if "access_token" not in result:
                login_result = login(email, password)
                if "access_token" in login_result:
                    return login_result
                else:
                    return {"error": "Регистрация успешна, но не удалось войти. Попробуйте войти вручную."}
            return result
        else:
            # Обрабатываем ошибки валидации
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and 'detail' in error_data:
                    detail = error_data['detail']
                    if isinstance(detail, list):
                        messages = []
                        for err in detail:
                            if err.get('type') == 'string_too_short':
                                messages.append("Пароль должен быть не менее 8 символов")
                            elif err.get('type') == 'value_error':
                                messages.append(err.get('msg', 'Ошибка валидации'))
                            else:
                                messages.append(err.get('msg', 'Ошибка'))
                        return {"error": "; ".join(messages)}
                    else:
                        return {"error": str(detail)}
                return {"error": "Ошибка регистрации"}
            except:
                return {"error": f"Ошибка регистрации (код {response.status_code})"}
    except requests.exceptions.ConnectionError:
        return {"error": "Не удалось подключиться к серверу"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}


def create_forecast(store_id, dept_ids: list, horizon_days: int, alpha: float):
    """Создать прогноз. store_id может быть строкой или списком."""
    payload = {
        "model_id": "m5_hurdle_v1",
        "store_id": store_id,
        "dept_ids": dept_ids,
        "horizon_days": horizon_days,
        "alpha": alpha
    }
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/forecast/run",
            json=payload,
            headers=get_headers()
        )
        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and 'detail' in error_data:
                    return {"error": str(error_data['detail'])}
                return {"error": f"Ошибка {response.status_code}"}
            except:
                return {"error": f"Ошибка {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}


def get_forecast_scenarios(forecast_id: int, item_id: str = None):
    url = f"{API_BASE_URL}/api/forecast/{forecast_id}/scenarios"
    if item_id:
        url += f"?item_id={item_id}"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None


# ==================== СТРАНИЦА АВТОРИЗАЦИИ ====================

def login_page():
    st.title("🔐 Авторизация")
    st.markdown("Введите email и пароль для доступа к системе прогнозирования")

    auth_mode = st.radio(
        "Выберите действие",
        ["🔑 Войти", "📝 Зарегистрироваться"],
        horizontal=True
    )

    email = st.text_input("Email", placeholder="admin@m5forecast.com")
    password = st.text_input("Пароль", type="password", placeholder="admin123")

    if auth_mode == "📝 Зарегистрироваться":
        username = st.text_input("Имя пользователя", placeholder="admin")
        confirm_password = st.text_input("Подтвердите пароль", type="password")
    else:
        username = None
        confirm_password = None

    if st.button("Продолжить", type="primary"):
        if not email or not password:
            st.error("Заполните все обязательные поля")
        elif auth_mode == "📝 Зарегистрироваться":
            if password != confirm_password:
                st.error("Пароли не совпадают!")
            elif len(password) < 8:
                st.error("Пароль должен быть не менее 8 символов")
            else:
                with st.spinner("Регистрация..."):
                    result = register(username, email, password)
                    if result and "access_token" in result:
                        st.session_state.token = result["access_token"]
                        st.session_state.user_info = result
                        st.success("Регистрация успешна! Добро пожаловать!")
                        st.rerun()
                    else:
                        error_msg = result.get("error", "Неизвестная ошибка") if result else "Неизвестная ошибка"
                        st.error(f"Ошибка регистрации: {error_msg}")
        else:
            with st.spinner("Авторизация..."):
                result = login(email, password)
                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user_info = result
                    st.success("Вход выполнен успешно!")
                    st.rerun()
                else:
                    error_msg = result.get("error",
                                           "Неверный email или пароль") if result else "Ошибка подключения к серверу"
                    st.error(error_msg)

    with st.expander("ℹ️ Демо-доступ"):
        st.markdown("""
        **Для тестирования используйте:**
        - Email: `admin@m5forecast.com`
        - Пароль: `admin123`
        """)


# ==================== ГЛАВНАЯ СТРАНИЦА ====================

def main_page():
    st.sidebar.title("📊 M5 Forecast Service")
    st.sidebar.markdown(f"**Пользователь:** {st.session_state.user_info.get('email', 'Неизвестно')}")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Навигация",
        ["🏠 Главная", "➕ Создать прогноз", "📋 История прогнозов", "📈 Результаты", "🎯 Сценарии"]
    )

    if st.sidebar.button("🚪 Выйти"):
        st.session_state.token = None
        st.session_state.user_info = None
        st.rerun()

    if page == "🏠 Главная":
        home_page()
    elif page == "➕ Создать прогноз":
        create_forecast_page()
    elif page == "📋 История прогнозов":
        history_page()
    elif page == "📈 Результаты":
        results_page()
    elif page == "🎯 Сценарии":
        scenarios_page()


# ==================== СТРАНИЦЫ ====================

def home_page():
    st.title("🏠 Добро пожаловать в систему прогнозирования спроса!")

    st.markdown("""
    ### 🎯 Возможности системы:

    1. **Прогнозирование спроса** на скоропортящиеся товары (FOODS_1, FOODS_2)
    2. **Управление рисками** через выбор квантиля (alpha)
    3. **Сравнение сценариев** для оптимизации закупок
    4. **Скачивание отчетов** в формате CSV

    ### 📊 Ключевые метрики:
    - **Baseline (alpha=0.5)**: Стандартный прогноз, высокий риск порчи
    - **Balanced (alpha=0.35)**: Сбалансированный подход
    - **Optimal (alpha=0.2)**: Оптимальный для скоропорта, снижение потерь на ~17%
    """)

    forecasts = get_forecasts()
    if forecasts:
        st.markdown("---")
        st.subheader("📈 Ваша статистика")
        col1, col2, col3 = st.columns(3)
        col1.metric("Всего прогнозов", len(forecasts.get('forecasts', [])))
        completed = sum(1 for f in forecasts.get('forecasts', []) if f['status'] == 'completed')
        col2.metric("Завершено", completed)
        col3.metric("В обработке", len(forecasts.get('forecasts', [])) - completed)


def create_forecast_page():
    st.title("➕ Создание нового прогноза")

    with st.form("forecast_form"):
        st.subheader("Параметры прогноза")

        # Выбор режима прогноза
        forecast_mode = st.radio(
            "Режим прогноза",
            ["🏪 Один магазин", "🏬 Несколько магазинов", "🗺️ Весь штат (CA)"],
            horizontal=True
        )

        # Выбор магазинов в зависимости от режима
        if forecast_mode == "🏪 Один магазин":
            selected_store = st.selectbox(
                "Магазин",
                ["CA_1", "CA_2", "CA_3", "CA_4"]
            )
            store_ids = [selected_store]
        elif forecast_mode == "🏬 Несколько магазинов":
            selected_stores = st.multiselect(
                "Выберите магазины",
                ["CA_1", "CA_2", "CA_3", "CA_4"],
                default=["CA_1"]
            )
            if not selected_stores:
                st.error("Выберите хотя бы один магазин")
                return
            store_ids = selected_stores
        else:  # Весь штат
            store_ids = ["CA_1", "CA_2", "CA_3", "CA_4"]
            st.info("📊 Будет создан прогноз по всем магазинам Калифорнии")

        dept_ids = st.multiselect(
            "Департаменты",
            ["FOODS_1", "FOODS_2"],
            default=["FOODS_1"],
            help="Выберите категории товаров (скоропорт)"
        )

        horizon_days = st.slider(
            "Горизонт прогноза (дней)",
            min_value=7,
            max_value=28,
            value=28,
            step=7,
            help="На сколько дней вперёд сделать прогноз"
        )

        alpha = st.slider(
            "Квантиль (alpha)",
            min_value=0.05,
            max_value=0.50,
            value=0.20,
            step=0.01,
            help="0.2 - оптимальный для скоропорта, 0.5 - baseline"
        )

        submitted = st.form_submit_button("🚀 Запустить прогноз", type="primary")

        if submitted:
            if not dept_ids:
                st.error("Выберите хотя бы один департамент")
            elif not store_ids:
                st.error("Выберите хотя бы один магазин")
            else:
                with st.spinner("Создание прогноза..."):
                    # Отправляем список или строку в зависимости от количества
                    store_id_param = store_ids if len(store_ids) > 1 else store_ids[0]
                    result = create_forecast(store_id_param, dept_ids, horizon_days, alpha)

                    # Проверяем результат
                    if result is None:
                        st.error("❌ Ошибка: сервер не ответил")
                    elif "error" in result:
                        st.error(f"❌ Ошибка: {result['error']}")
                    elif "forecast_id" in result:
                        st.success(f"✅ Прогноз #{result['forecast_id']} создан!")
                        st.info(f"📊 Магазины: {', '.join(store_ids)}")
                        st.info(f"📈 Статус: {result.get('status', 'unknown')}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Неизвестный ответ сервера: {result}")


def history_page():
    st.title("📋 История прогнозов")

    with st.spinner("Загрузка истории..."):
        forecasts = get_forecasts()

    if forecasts and forecasts.get('forecasts'):
        df = pd.DataFrame(forecasts['forecasts'])

        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        if 'completed_at' in df.columns:
            df['completed_at'] = pd.to_datetime(df['completed_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(
            df[['forecast_id', 'store_id', 'status', 'alpha', 'horizon_days', 'created_at', 'completed_at']],
            use_container_width=True
        )

        status_counts = df['status'].value_counts()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Всего", len(df))
        col2.metric("Завершено", status_counts.get('completed', 0))
        col3.metric("В обработке", status_counts.get('processing', 0))
        col4.metric("Ошибки", status_counts.get('failed', 0))
    else:
        st.info("История прогнозов пуста")


def results_page():
    st.title("📈 Результаты прогноза")

    forecasts = get_forecasts()
    if not forecasts or not forecasts.get('forecasts'):
        st.info("Нет доступных прогнозов")
        return

    completed_forecasts = [f for f in forecasts['forecasts'] if f['status'] == 'completed']
    if not completed_forecasts:
        st.warning("Нет завершённых прогнозов")
        return

    forecast_id = st.selectbox(
        "Выберите прогноз",
        [f['forecast_id'] for f in completed_forecasts],
        format_func=lambda x: f"Прогноз #{x}"
    )

    if forecast_id:
        with st.spinner("Загрузка результатов..."):
            summary = get_forecast_summary(forecast_id)

        if summary:
            st.subheader(f"Прогноз #{summary['forecast_id']}")
            st.markdown(
                f"**Магазин:** {summary['store_id']} | **Период:** {summary['period_start']} - {summary['period_end']}")
            st.markdown(
                f"**Товаров:** {summary['total_items']} | **Всего к заказу:** {summary['total_order_recommendation']}")

            df = pd.DataFrame(summary['items'])

            risk_filter = st.multiselect(
                "Фильтр по уровню риска",
                df['risk_level'].unique(),
                default=df['risk_level'].unique()
            )
            df_filtered = df[df['risk_level'].isin(risk_filter)]

            st.dataframe(
                df_filtered[['item_id', 'total_predicted_sales', 'recommended_order', 'risk_level', 'risk_description',
                             'avg_daily_sales']],
                use_container_width=True
            )

            # График 1: Топ-20 товаров
            st.subheader("📊 Топ-20 товаров по рекомендуемому заказу")
            top_20 = df.nlargest(20, 'recommended_order')
            fig = px.bar(
                top_20,
                x='item_id',
                y='recommended_order',
                color='risk_level',
                title='Топ-20 товаров по объёму заказа',
                labels={'item_id': 'Товар', 'recommended_order': 'Рекомендуемый заказ'}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label="📥 Скачать график (PNG)",
                data=fig.to_image(format="png", width=1200, height=600),
                file_name=f"forecast_{forecast_id}_top20.png",
                mime="image/png"
            )

            # График 2: Распределение рисков
            st.subheader("📊 Распределение товаров по риску")
            risk_counts = df['risk_level'].value_counts()
            fig_pie = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title='Распределение по уровню риска',
                color_discrete_map={'low': 'green', 'medium': 'orange', 'high': 'red'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            st.download_button(
                label="📥 Скачать график (PNG)",
                data=fig_pie.to_image(format="png", width=800, height=600),
                file_name=f"forecast_{forecast_id}_risk_distribution.png",
                mime="image/png"
            )


def scenarios_page():
    st.title("🎯 Сравнение сценариев")

    forecasts = get_forecasts()
    if not forecasts or not forecasts.get('forecasts'):
        st.info("Нет доступных прогнозов")
        return

    completed_forecasts = [f for f in forecasts['forecasts'] if f['status'] == 'completed']
    if not completed_forecasts:
        st.warning("Нет завершённых прогнозов")
        return

    forecast_id = st.selectbox(
        "Выберите прогноз",
        [f['forecast_id'] for f in completed_forecasts],
        format_func=lambda x: f"Прогноз #{x}"
    )

    if forecast_id:
        item_id = st.text_input("ID товара (опционально)", placeholder="FOODS_1_018")

        if st.button("🔍 Загрузить сценарии", type="primary"):
            progress_bar = st.progress(0)
            progress_text = st.empty()

            with st.spinner("Загрузка сценариев (может занять около 40 секунд)..."):
                scenarios = None
                for i in range(100):
                    time.sleep(0.4)
                    progress_bar.progress(i + 1)
                    progress_text.text(f"Обработка сценариев... {i + 1}%")

                    if i == 99:
                        scenarios = get_forecast_scenarios(forecast_id, item_id if item_id else None)

            progress_bar.empty()
            progress_text.empty()

            if scenarios:
                st.subheader(f"Сценарии для прогноза #{scenarios['forecast_id']}")
                st.markdown(f"**Магазин:** {scenarios['store_id']} | **Период:** {scenarios['period']}")
                st.markdown(f"**Товаров:** {scenarios['total_items']}")

                rows = []
                for item in scenarios['items']:
                    for scenario_name in ['baseline', 'balanced', 'optimal', 'your_variant']:
                        scenario = item[scenario_name]
                        rows.append({
                            'item_id': item['item_id'],
                            'scenario': scenario_name,
                            'alpha': scenario['alpha'],
                            'recommended_order': scenario['recommended_order'],
                            'risk': scenario['risk']
                        })

                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)

                if len(scenarios['items']) > 0:
                    selected_item = st.selectbox(
                        "Выберите товар для детального анализа",
                        [item['item_id'] for item in scenarios['items']]
                    )

                    item_data = next(item for item in scenarios['items'] if item['item_id'] == selected_item)

                    fig = go.Figure()
                    colors = {'baseline': 'red', 'balanced': 'orange', 'optimal': 'green', 'your_variant': 'blue'}

                    for scenario_name in ['baseline', 'balanced', 'optimal', 'your_variant']:
                        scenario = item_data[scenario_name]
                        fig.add_trace(go.Bar(
                            name=scenario_name,
                            x=[scenario_name],
                            y=[scenario['recommended_order']],
                            marker_color=colors[scenario_name],
                            text=[f"alpha={scenario['alpha']}"],
                            textposition='outside'
                        ))

                    fig.update_layout(
                        title=f'Сравнение сценариев для {selected_item}',
                        xaxis_title='Сценарий',
                        yaxis_title='Рекомендуемый заказ',
                        barmode='group'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("📊 Описание сценариев")
                    for scenario_name in ['baseline', 'balanced', 'optimal', 'your_variant']:
                        scenario = item_data[scenario_name]
                        st.markdown(f"**{scenario_name.upper()}** (alpha={scenario['alpha']}): {scenario['risk']}")


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == "__main__":
    if st.session_state.token is None:
        login_page()
    else:
        main_page()
