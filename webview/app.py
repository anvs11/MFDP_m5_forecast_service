import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import time

API_BASE_URL = "http://app:8080"


# Кэширование
def get_forecasts():
    """Получить список прогнозов"""
    token = st.session_state.token
    if not token:
        return None
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/forecast/history",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

@st.cache_data(ttl=10, show_spinner=False)
def get_forecast_status_cached(forecast_id: int, token: str):
    """Получить статус прогноза (кэш 10 сек — статус может меняться)"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/forecast/{forecast_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def get_forecast_status(forecast_id: int):
    """Обёртка с передачей токена"""
    token = st.session_state.token
    if not token:
        return None
    return get_forecast_status_cached(forecast_id, token)


@st.cache_data(ttl=600, show_spinner=False)
def get_forecast_summary_cached(forecast_id: int, token: str):
    """Получить summary прогноза (кэш 10 мин — не меняется после завершения)"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/forecast/{forecast_id}/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def get_forecast_summary(forecast_id: int):
    """Обёртка с передачей токена"""
    token = st.session_state.token
    if not token:
        return None
    return get_forecast_summary_cached(forecast_id, token)

# Инициализация
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None


# Функции API
def get_headers():
    """Получить заголовки с токеном"""
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
        if response.status_code in [200, 201]:
            result = response.json()
            if "access_token" not in result:
                login_result = login(email, password)
                if "access_token" in login_result:
                    return login_result
                else:
                    return {"error": "Регистрация успешна, но не удалось войти. Попробуйте войти вручную."}
            return result
        else:
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and 'detail' in error_data:
                    detail = error_data['detail']
                    if isinstance(detail, list):
                        messages = []
                        for err in detail:
                            if err.get('type') == 'string_too_short':
                                messages.append("Пароль должен быть не менее 8 символов")
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


def create_forecast(store_id: str, dept_ids: list, horizon_days: int, alpha: float):
    """Создать прогноз для ОДНОГО магазина"""
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
            headers=get_headers(),
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result
        else:
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and 'detail' in error_data:
                    return {"error": str(error_data['detail'])}
                return {"error": f"Ошибка {response.status_code}"}
            except:
                return {"error": f"Ошибка {response.status_code}"}

    except requests.exceptions.ConnectionError:
        return {"error": "Не удалось подключиться к серверу"}
    except requests.exceptions.Timeout:
        return {"error": "Превышено время ожидания ответа от сервера"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}


def get_forecast_scenarios(forecast_id: int, item_id: str = None):
    """Получить сценарии прогноза"""
    url = f"{API_BASE_URL}/api/forecast/{forecast_id}/scenarios"
    if item_id:
        url += f"?item_id={item_id}"
    try:
        response = requests.get(url, headers=get_headers(), timeout=120)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None

def get_user_balance():
    """Получить баланс пользователя"""
    token = st.session_state.token
    if not token:
        return None
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/users/me/balance",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('balance', 0)
        return None
    except Exception as e:
        return None


def recharge_balance(amount: float):
    """Пополнить баланс"""
    token = st.session_state.token
    if not token:
        return {"error": "Не авторизован"}
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/users/me/recharge",
            json={"amount": amount},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_data = response.json()
                return {"error": error_data.get('detail', f"Ошибка {response.status_code}")}
            except:
                return {"error": f"Ошибка {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def get_transactions():
    """Получить историю транзакций"""
    token = st.session_state.token
    if not token:
        return None
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/users/me/transactions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# Страница авторизации
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


# Главная страница
def main_page():
    balance_info = get_user_balance()
    balance_text = f"${balance_info:.2f}" if balance_info is not None else "N/A"

    st.sidebar.title("📊 M5 Forecast Service")
    st.sidebar.markdown(f"**Пользователь:** {st.session_state.user_info.get('email', 'Неизвестно')}")
    st.sidebar.markdown(f"**💰 Баланс:** {balance_text}")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Навигация",
        ["🏠 Главная", "➕ Создать прогноз", "📈 Результаты", "🎯 Сценарии", "🏬 Сравнение магазинов", "👤 Личный кабинет"]
    )

    if st.sidebar.button("🚪 Выйти"):
        st.session_state.token = None
        st.session_state.user_info = None
        st.rerun()

    if page == "🏠 Главная":
        home_page()
    elif page == "➕ Создать прогноз":
        create_forecast_page()
    elif page == "📈 Результаты":
        results_page()
    elif page == "🎯 Сценарии":
        scenarios_page()
    elif page == "🏬 Сравнение магазинов":
        compare_stores_page()
    elif page == "👤 Личный кабинет":
        profile_page()


#  Страницы
def home_page():
    st.title("🏠 Добро пожаловать в систему прогнозирования спроса!")

    balance = get_user_balance()
    if balance is not None:
        if balance < 6:
            st.warning(f"⚠️ **Ваш баланс:** ${balance:.2f} — недостаточно средств для новых прогнозов")
        else:
            st.success(f"💰 **Ваш баланс:** ${balance:.2f}")

    st.markdown("""
    ### 🎯 Возможности системы:

    1. **Прогнозирование спроса** на скоропортящиеся товары (FOODS_1, FOODS_2)
    2. **Управление рисками** через выбор квантиля (alpha)
    3. **Сравнение сценариев** для оптимизации закупок
    4. **Сравнение магазинов** для выбора оптимальной стратегии
    5. **Скачивание отчетов** в формате CSV

    ### 📊 Ключевые метрики:
    - **Baseline (alpha=0.5)**: Стандартный прогноз, высокий риск порчи
    - **Balanced (alpha=0.35)**: Сбалансированный подход
    - **Optimal (alpha=0.2)**: Оптимальный для скоропорта, снижение потерь на ~17%
    """)

    forecasts = get_forecasts()
    if forecasts:
        st.markdown("---")
        st.subheader(" Ваша статистика")
        col1, col2, col3 = st.columns(3)
        col1.metric("Всего прогнозов", len(forecasts.get('forecasts', [])))
        completed = sum(1 for f in forecasts.get('forecasts', []) if f['status'] == 'completed')
        col2.metric("Завершено", completed)
        col3.metric("В обработке", len(forecasts.get('forecasts', [])) - completed)

def create_forecast_page():
    st.title("➕ Создание нового прогноза")

    with st.form("forecast_form"):
        st.subheader("Параметры прогноза")

        # Только один магазин
        store_id = st.selectbox(
            " Выберите магазин",
            ["CA_1", "CA_2", "CA_3", "CA_4"],
            help="Выберите один магазин для прогнозирования"
        )

        dept_ids = st.multiselect(
            "📦 Департаменты",
            ["FOODS_1", "FOODS_2"],
            default=["FOODS_1"],
            help="Выберите категории товаров (скоропорт)"
        )

        horizon_days = st.slider(
            " Горизонт прогноза (дней)",
            min_value=7,
            max_value=28,
            value=28,
            step=7,
            help="На сколько дней вперёд сделать прогноз"
        )

        alpha = st.slider(
            "📊 Квантиль (alpha)",
            min_value=0.05,
            max_value=0.50,
            value=0.20,
            step=0.01,
            help="0.2 - оптимальный для скоропорта, 0.5 - baseline"
        )

        submitted = st.form_submit_button("🚀 Запустить прогноз", type="primary", use_container_width=True)

        if submitted:
            if not dept_ids:
                st.error("❌ Выберите хотя бы один департамент")
            else:
                result = create_forecast(store_id, dept_ids, horizon_days, alpha)

                if result is None:
                    st.error("❌ Ошибка: сервер не ответил")
                    st.stop()
                elif "forecast_id" in result:
                    get_forecast_summary_cached.clear()
                    get_forecast_status_cached.clear()

                    st.success(f"✅ Прогноз #{result['forecast_id']} успешно создан!")
                    st.info(f"📍 Магазин: {store_id}")
                    st.info(f"📈 Статус: {result.get('status', 'processing')}")

                    with st.spinner("⏳ Прогноз обрабатывается... Обычно это занимает 10-30 секунд."):
                        progress_bar = st.progress(0)
                        status_container = st.empty()

                        max_wait = 60
                        start_time = time.time()
                        current_status = "processing"

                        while time.time() - start_time < max_wait:
                            status_data = get_forecast_status(result['forecast_id'])

                            if status_data:
                                current_status = status_data.get('status', 'processing')

                                if current_status == 'completed':
                                    progress_bar.progress(100)
                                    status_container.success("✅ Прогноз обработан!")
                                    break
                                elif current_status == 'failed':
                                    progress_bar.empty()
                                    status_container.error("❌ Прогноз не удалось обработать")
                                    st.error(f"Ошибка: {status_data.get('error', 'Неизвестная ошибка')}")
                                    time.sleep(20)
                                    st.rerun()
                                    break
                                else:
                                    elapsed = time.time() - start_time
                                    progress = min(int((elapsed / max_wait) * 100), 90)
                                    progress_bar.progress(progress)
                                    status_container.info(f"⏳ Статус: {current_status}...")

                            time.sleep(2)

                        # Таймаут
                        if current_status not in ['completed', 'failed']:
                            status_container.warning(
                                "⏱️ Превышено время ожидания. Проверьте статус на вкладке Результаты")

                    if current_status == 'completed':
                        st.success(
                            "📈 С результатами работы сервиса можно ознакомиться на вкладке **📈 Результаты**")
                        time.sleep(120)
                        st.rerun()

                    elif result.get("error") is not None:
                        st.error(f"❌ Ошибка: {result['error']}")
                    else:
                        st.error(f"❌ Неизвестный ответ сервера: {result}")

def results_page():
    st.title(" Результаты прогноза")

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
                df_filtered[['item_id', 'recommended_order', 'risk_level', 'risk_description']],
                use_container_width=True,
                column_config={
                    "item_id": "ID товара",
                    "recommended_order": st.column_config.NumberColumn("Рекомендуемый заказ", format="%.0f"),
                    "risk_level": "Уровень риска",
                    "risk_description": "Описание"
                }
            )

            st.subheader("📥 Скачать отчет")

            csv_summary = df_filtered[
                ['item_id', 'total_predicted_sales', 'recommended_order', 'risk_level', 'risk_description']].to_csv(
                index=False).encode('utf-8')
            st.download_button(
                label="📥 Скачать план закупок (CSV)",
                data=csv_summary,
                file_name=f"forecast_{forecast_id}_summary.csv",
                mime="text/csv",
                key='download-summary'
            )

            detailed_response = requests.get(
                f"{API_BASE_URL}/api/forecast/{forecast_id}/download?format=detailed",
                headers=get_headers()
            )
            if detailed_response.status_code == 200:
                st.download_button(
                    label="📥 Скачать детальный прогноз (CSV)",
                    data=detailed_response.content,
                    file_name=f"forecast_{forecast_id}_detailed.csv",
                    mime="text/csv",
                    key='download-detailed'
                )

            # График 1: Топ-20 товаров
            st.subheader(" Топ-20 товаров по рекомендуемому заказу")
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
                label=" Скачать график (PNG)",
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
            with st.spinner("Загрузка сценариев (может занять 30-40 секунд)..."):
                scenarios = get_forecast_scenarios(
                    forecast_id,
                    item_id.strip() if item_id.strip() else None
                )

            if scenarios:
                st.session_state.scenarios_data = scenarios
                st.session_state.scenarios_item_id = item_id.strip() if item_id.strip() else None

        if st.session_state.get('scenarios_data'):
            scenarios = st.session_state.scenarios_data
            item_id = st.session_state.get('scenarios_item_id')

            st.subheader(f"Сценарии для прогноза #{scenarios['forecast_id']}")
            st.markdown(f"**Магазин:** {scenarios['store_id']} | **Период:** {scenarios['period']}")
            st.markdown(f"**Товаров:** {scenarios['total_items']}")

            if item_id:
                st.info(f"🔍 Фильтр по товару: **{item_id}**")

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

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Скачать сценарии (CSV)",
                data=csv,
                file_name=f"forecast_{scenarios['forecast_id']}_scenarios.csv",
                mime="text/csv"
            )

            if item_id and len(scenarios['items']) > 0:
                st.markdown("---")
                st.subheader(f"📊 Сравнение сценариев для {item_id}")

                item_data = scenarios['items'][0]

                fig = go.Figure()
                colors = {'baseline': 'red', 'balanced': 'orange', 'optimal': 'green', 'your_variant': 'blue'}

                scenario_data = []
                for scenario_name in ['baseline', 'balanced', 'optimal', 'your_variant']:
                    if scenario_name in item_data:
                        scenario = item_data[scenario_name]
                        recommended_order = scenario.get('recommended_order', 0)
                        alpha = scenario.get('alpha', 0)
                        scenario_data.append({
                            'name': scenario_name,
                            'order': recommended_order,
                            'alpha': alpha
                        })
                for data in scenario_data:
                    fig.add_trace(go.Bar(
                        name=data['name'],
                        x=[data['name']],
                        y=[data['order']],
                        marker_color=colors.get(data['name'], 'gray'),
                        text=[f"alpha={data['alpha']}<br>order={data['order']}"],
                        textposition='outside',
                        hovertemplate=f"<b>{data['name']}</b><br>alpha={data['alpha']}<br>Заказ: {data['order']}<extra></extra>"
                    ))

                max_value = max([d['order'] for d in scenario_data]) if scenario_data else 10
                if max_value == 0:
                    max_value = 10

                fig.update_layout(
                    title=f'Сравнение сценариев для {item_id}',
                    xaxis_title='Сценарий',
                    yaxis_title='Рекомендуемый заказ',
                    yaxis=dict(range=[0, max_value * 1.3]),
                    barmode='group',
                    showlegend=True,
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)

                st.download_button(
                    label="📥 Скачать график (PNG)",
                    data=fig.to_image(format="png", width=1200, height=600),
                    file_name=f"forecast_{scenarios['forecast_id']}_{item_id}_scenarios.png",
                    mime="image/png"
                )

def compare_stores_page():
    st.title("🏬 Сравнение магазинов")

    st.markdown("""
    ### 📊 Как это работает:
    1. Выберите 2-4 магазина для сравнения
    2. Система создаст отдельный прогноз для каждого магазина
    3. Результаты будут отображены на сравнительном графике

    ⏱️ **Время выполнения:** ~30 секунд на магазин
    """)

    # Выбор магазинов
    stores_to_compare = st.multiselect(
        "📍 Выберите магазины для сравнения",
        ["CA_1", "CA_2", "CA_3", "CA_4"],
        default=["CA_1", "CA_2"],
        help="Выберите от 2 до 4 магазинов"
    )

    dept_ids = st.multiselect(
        "📦 Департаменты",
        ["FOODS_1", "FOODS_2"],
        default=["FOODS_1"]
    )

    horizon_days = st.slider(
        "📅 Горизонт прогноза (дней)",
        min_value=7,
        max_value=28,
        value=28,
        step=7
    )

    alpha = st.slider(
        "📊 Квантиль (alpha)",
        min_value=0.05,
        max_value=0.50,
        value=0.20,
        step=0.01
    )

    if st.button("🚀 Запустить сравнение", type="primary", use_container_width=True):
        if len(stores_to_compare) < 2:
            st.error("❌ Выберите хотя бы 2 магазина")
            st.stop()
        elif not dept_ids:
            st.error("❌ Выберите хотя бы один департамент")
            st.stop()
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            forecast_ids = []

            for i, store_id in enumerate(stores_to_compare):
                status_text.text(f"🔄 Создание прогноза для {store_id} ({i + 1}/{len(stores_to_compare)})...")

                result = create_forecast(store_id, dept_ids, horizon_days, alpha)

                if result and "forecast_id" in result:
                    forecast_ids.append({
                        'store_id': store_id,
                        'forecast_id': result['forecast_id']
                    })
                elif result and result.get("error") is not None:
                    st.error(f"❌ Ошибка при создании прогноза для {store_id}: {result['error']}")
                else:
                    st.error(f"❌ Ошибка при создании прогноза для {store_id}: неизвестный ответ")

                progress_bar.progress((i + 1) / len(stores_to_compare))

            status_text.text("✅ Все прогнозы созданы! Ожидаем завершения обработки...")

            max_wait = 180
            start_time = time.time()
            all_completed = False

            while time.time() - start_time < max_wait:
                all_completed = True
                for fc in forecast_ids:
                    status = get_forecast_status(fc['forecast_id'])
                    if status and status.get('status') != 'completed':
                        all_completed = False
                        break

                if all_completed:
                    break

                time.sleep(2)

            st.subheader(" Результаты сравнения")

            comparison_data = []

            for fc in forecast_ids:
                summary = get_forecast_summary(fc['forecast_id'])
                if summary:
                    total_items = summary['total_items']
                    total_order = summary['total_order_recommendation']
                    avg_order = total_order / total_items if total_items > 0 else 0

                    risk_counts = {}
                    for item in summary['items']:
                        risk = item['risk_level']
                        risk_counts[risk] = risk_counts.get(risk, 0) + 1

                    comparison_data.append({
                        'store_id': fc['store_id'],
                        'total_items': total_items,
                        'total_order': total_order,
                        'avg_order_per_item': round(avg_order, 2),
                        'high_risk': risk_counts.get('high', 0),
                        'medium_risk': risk_counts.get('medium', 0),
                        'low_risk': risk_counts.get('low', 0)
                    })

            if comparison_data:
                df = pd.DataFrame(comparison_data)

                # График 1: Общий заказ по магазинам
                st.subheader("📦 Общий объём заказа по магазинам")
                fig = go.Figure()

                fig.add_trace(go.Bar(
                    name='Общий заказ',
                    x=df['store_id'],
                    y=df['total_order'],
                    marker_color='blue',
                    text=df['total_order'],
                    textposition='outside'
                ))

                fig.update_layout(
                    title='Сравнение общего объёма заказа',
                    xaxis_title='Магазин',
                    yaxis_title='Количество единиц к заказу',
                    barmode='group'
                )
                st.plotly_chart(fig, use_container_width=True)

                st.download_button(
                    label="📥 Скачать график (PNG)",
                    data=fig.to_image(format="png", width=1200, height=600),
                    file_name="stores_comparison_total_order.png",
                    mime="image/png"
                )

                # График 2: Распределение рисков
                st.subheader("️ Распределение товаров по уровню риска")
                fig_risk = go.Figure()

                fig_risk.add_trace(go.Bar(
                    name='Высокий риск',
                    x=df['store_id'],
                    y=df['high_risk'],
                    marker_color='red'
                ))
                fig_risk.add_trace(go.Bar(
                    name='Средний риск',
                    x=df['store_id'],
                    y=df['medium_risk'],
                    marker_color='orange'
                ))
                fig_risk.add_trace(go.Bar(
                    name='Низкий риск',
                    x=df['store_id'],
                    y=df['low_risk'],
                    marker_color='green'
                ))

                fig_risk.update_layout(
                    title='Распределение рисков по магазинам',
                    xaxis_title='Магазин',
                    yaxis_title='Количество товаров',
                    barmode='stack'
                )
                st.plotly_chart(fig_risk, use_container_width=True)

                st.download_button(
                    label="📥 Скачать график (PNG)",
                    data=fig_risk.to_image(format="png", width=1200, height=600),
                    file_name="stores_comparison_risk.png",
                    mime="image/png"
                )

                # Таблица результатов
                st.subheader(" Сводная таблица")
                st.dataframe(df, use_container_width=True)

                # Кнопка скачивания CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Скачать сравнение (CSV)",
                    data=csv,
                    file_name="stores_comparison.csv",
                    mime="text/csv"
                )
            else:
                st.error("❌ Не удалось получить результаты прогнозов")


def profile_page():
    st.title("👤 Личный кабинет")

    st.subheader("📋 Информация о пользователе")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Email:** {st.session_state.user_info.get('email', 'N/A')}")
        st.markdown(f"**User ID:** {st.session_state.user_info.get('user_id', 'N/A')}")

    with col2:
        balance = get_user_balance()
        if balance is not None:
            st.metric("💰 Текущий баланс", f"${balance:.2f}")
        else:
            st.warning("Не удалось получить баланс")

    st.markdown("---")

    st.subheader("💳 Пополнение баланса")
    st.info("💡 Демо-режим: пополнение не требует реальных платежей")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("+$10", use_container_width=True):
            result = recharge_balance(10)
            if "error" not in result:
                st.success("✅ Баланс пополнен на $10")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"❌ {result['error']}")

    with col2:
        if st.button("+$50", use_container_width=True):
            result = recharge_balance(50)
            if "error" not in result:
                st.success("✅ Баланс пополнен на $50")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"❌ {result['error']}")

    with col3:
        if st.button("+$100", use_container_width=True):
            result = recharge_balance(100)
            if "error" not in result:
                st.success("✅ Баланс пополнен на $100")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"❌ {result['error']}")

    with col4:
        custom_amount = st.number_input("Своя сумма ($)", min_value=1.0, value=25.0, step=5.0)
        if st.button("Пополнить", use_container_width=True):
            result = recharge_balance(custom_amount)
            if "error" not in result:
                st.success(f"✅ Баланс пополнен на ${custom_amount}")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"❌ {result['error']}")

    st.markdown("---")

    st.subheader("📜 История транзакций")

    if st.button("🔄 Обновить транзакции"):
        st.rerun()

    transactions = get_transactions()

    if transactions and transactions.get('transactions'):
        df = pd.DataFrame(transactions['transactions'])

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')

        def format_amount(row):
            if row['tx_type'] == 'recharge':
                return f"+${row['amount']:.2f}"
            else:
                return f"-${abs(row['amount']):.2f}"

        df['amount_formatted'] = df.apply(format_amount, axis=1)

        st.dataframe(
            df[['tx_id', 'amount_formatted', 'tx_type', 'description', 'timestamp']].rename(columns={
                'tx_id': 'ID транзакции',
                'amount_formatted': 'Сумма',
                'tx_type': 'Тип',
                'description': 'Описание',
                'timestamp': 'Дата'
            }),
            use_container_width=True,
            hide_index=True
        )

        col1, col2, col3 = st.columns(3)
        recharges = df[df['tx_type'] == 'recharge']['amount'].sum()
        spends = df[df['tx_type'] == 'forecast']['amount'].sum() if 'forecast' in df['tx_type'].values else 0

        col1.metric("Всего пополнений", f"${recharges:.2f}")
        col2.metric("Всего потрачено", f"${abs(spends):.2f}")
        col3.metric("Всего транзакций", len(df))
    else:
        st.info("📭 История транзакций пуста")

# Запуск приложения
if __name__ == "__main__":
    if st.session_state.token is None:
        login_page()
    else:
        main_page()
